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

    try:
        response = requests.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
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
