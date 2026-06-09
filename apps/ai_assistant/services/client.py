"""Thin Gemini REST client.

No dependency on ``google-generativeai`` so we keep the install footprint
small — the official SDK pulls in grpc, protobuf, and a chain of
google-auth packages just to wrap the same JSON endpoint we hit here.

Raises :class:`GeminiUnavailable` on every failure mode (missing key,
network error, malformed response, safety block). The caller is
expected to catch this and degrade gracefully — never let a flaky
upstream surface as a 500.
"""
from __future__ import annotations

import logging

import requests
from django.conf import settings

logger = logging.getLogger("merrymeal.ai_assistant")

_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)
_TIMEOUT_SECONDS = 15
_MAX_OUTPUT_TOKENS = 512
_TEMPERATURE = 0.7


class GeminiUnavailable(Exception):
    """Raised on any failure path. The message is for logs, not users —
    views must render their own user-facing fallback copy."""


def generate(
    system: str,
    user_message: str,
    *,
    history: list[dict] | None = None,
) -> str:
    """Call Gemini and return the model's text reply.

    ``system`` is the system instruction (data context + behaviour rules).
    ``user_message`` is the latest member input. ``history`` is an optional
    list of ``{"role": "user"|"model", "text": "..."}`` dicts for
    conversational continuity — keep it short (the system prompt already
    carries the per-request data context, so long histories add cost
    without much benefit).
    """
    api_key = getattr(settings, "GEMINI_API_KEY", "") or ""
    if not api_key:
        raise GeminiUnavailable("GEMINI_API_KEY is not set")

    model = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
    url = _ENDPOINT.format(model=model)

    contents: list[dict] = []
    for turn in history or []:
        contents.append(
            {"role": turn["role"], "parts": [{"text": turn["text"]}]}
        )
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {
            "temperature": _TEMPERATURE,
            "maxOutputTokens": _MAX_OUTPUT_TOKENS,
        },
    }

    # Valid Gemini-capable keys come in two flavours:
    #   * AI Studio keys ``AIzaSy...`` — free tier, easy path, the one
    #     we recommend.
    #   * Google Cloud API keys ``AQ.Ab...`` — work IF the project has
    #     the "Generative Language API" enabled. Useful when the
    #     charity already has a GCP project for other services.
    # Anything else (OAuth access tokens ``ya29...``, service-account
    # JSON, raw bearer tokens) belongs at a different endpoint and
    # will 401 here. Warn early so the operator sees the cause in the
    # log instead of a silent fallback.
    _VALID_PREFIXES = ("AIza", "AQ.")
    if not any(api_key.startswith(p) for p in _VALID_PREFIXES):
        logger.warning(
            "GEMINI_API_KEY does not look like a Gemini-capable key "
            "(expected prefix 'AIza...' from AI Studio or 'AQ....' "
            "from Google Cloud). Got prefix=%r. Generate one at "
            "https://aistudio.google.com/apikey.",
            api_key[:6],
        )
        raise GeminiUnavailable("wrong key format (expected 'AIza...' or 'AQ....')")

    try:
        response = requests.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except requests.HTTPError as exc:
        # 401/403 → bad key; surface the upstream message so the dev
        # log shows "API key not valid" instead of a generic "network".
        body = exc.response.text[:300] if exc.response is not None else ""
        logger.warning("Gemini HTTP %s: %s", exc.response.status_code if exc.response else "?", body)
        raise GeminiUnavailable(f"http {exc.response.status_code if exc.response else '?'}: {body}") from exc
    except requests.RequestException as exc:
        logger.warning("Gemini network error: %s", exc)
        raise GeminiUnavailable(f"network: {exc}") from exc
    except ValueError as exc:
        logger.warning("Gemini returned non-JSON: %s", exc)
        raise GeminiUnavailable(f"decode: {exc}") from exc

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        # Gemini surfaces safety blocks as ``promptFeedback.blockReason``
        # with no ``candidates`` — log and fall back, never show the raw
        # reason to the member.
        logger.warning("Gemini returned no text: %s", data)
        raise GeminiUnavailable(f"empty response: {exc}") from exc
