"""Thin Anthropic Messages API client.

No dependency on the ``anthropic`` SDK so we keep the install footprint
small — the official SDK pulls in httpx, pydantic, anyio, and a chain
of typing-compat packages just to wrap the same JSON endpoint we hit
here. The Messages API is stable and well documented; speaking HTTP
directly is roughly fifty lines of code.

Raises :class:`ClaudeUnavailable` on every failure mode (missing key,
network error, malformed response, safety stop, refusal). The caller
is expected to catch this and degrade gracefully — never let a flaky
upstream surface as a 500.
"""
from __future__ import annotations

import logging

import requests
from django.conf import settings

logger = logging.getLogger("merrymeal.ai_assistant")

_ENDPOINT = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"
_TIMEOUT_SECONDS = 15
_MAX_OUTPUT_TOKENS = 512
_TEMPERATURE = 0.7

# History uses the role name ``"assistant"`` for prior model turns —
# that matches the Anthropic Messages API and the role name we store
# in the session. ``"model"`` is accepted as a legacy alias from older
# session payloads, so a logged-in member with a half-finished
# transcript doesn't lose their history on deploy.
_ASSISTANT_ROLES = {"assistant", "model"}


class ClaudeUnavailable(Exception):
    """Raised on any failure path. The message is for logs, not users —
    views must render their own user-facing fallback copy."""


def generate(
    system: str,
    user_message: str,
    *,
    history: list[dict] | None = None,
) -> str:
    """Call Claude and return the model's text reply.

    ``system`` is the system instruction (data context + behaviour rules).
    ``user_message`` is the latest member input. ``history`` is an
    optional list of ``{"role": "user"|"assistant", "text": "..."}``
    dicts for conversational continuity — keep it short (the system
    prompt already carries the per-request data context, so long
    histories add cost without much benefit).
    """
    api_key = getattr(settings, "ANTHROPIC_API_KEY", "") or ""
    if not api_key:
        raise ClaudeUnavailable("ANTHROPIC_API_KEY is not set")

    model = getattr(settings, "ANTHROPIC_MODEL", "claude-haiku-4-5")

    messages: list[dict] = []
    for turn in history or []:
        role = "assistant" if turn["role"] in _ASSISTANT_ROLES else "user"
        messages.append({"role": role, "content": turn["text"]})
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": model,
        "max_tokens": _MAX_OUTPUT_TOKENS,
        "temperature": _TEMPERATURE,
        "system": system,
        "messages": messages,
    }

    # Anthropic keys start ``sk-ant-``. Warn early if the operator
    # pasted something else (a Gemini key, an OpenAI key, an OAuth
    # token) so the dev log shows the cause instead of a silent fallback.
    if not api_key.startswith("sk-ant-"):
        logger.warning(
            "ANTHROPIC_API_KEY does not look like an Anthropic key "
            "(expected prefix 'sk-ant-...'). Got prefix=%r. Generate "
            "one at https://console.anthropic.com/settings/keys.",
            api_key[:7],
        )
        raise ClaudeUnavailable("wrong key format (expected 'sk-ant-...')")

    try:
        response = requests.post(
            _ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": _API_VERSION,
            },
            json=payload,
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except requests.HTTPError as exc:
        # 401/403 → bad key, 429 → over rate limit. Surface the upstream
        # message in the log so the dev sees the exact reason.
        body = exc.response.text[:300] if exc.response is not None else ""
        status = exc.response.status_code if exc.response is not None else "?"
        logger.warning("Claude HTTP %s: %s", status, body)
        raise ClaudeUnavailable(f"http {status}: {body}") from exc
    except requests.RequestException as exc:
        logger.warning("Claude network error: %s", exc)
        raise ClaudeUnavailable(f"network: {exc}") from exc
    except ValueError as exc:
        logger.warning("Claude returned non-JSON: %s", exc)
        raise ClaudeUnavailable(f"decode: {exc}") from exc

    # Anthropic returns ``content`` as a list of typed blocks. For a
    # plain text reply there's exactly one ``{"type": "text", ...}``
    # block. A refusal or safety stop comes back with ``stop_reason``
    # set to ``refusal`` / ``end_turn`` but no usable text — treat
    # that as unavailable so the view renders the static fallback
    # instead of a blank bubble.
    try:
        blocks = data["content"]
        text_parts = [b["text"] for b in blocks if b.get("type") == "text"]
        text = "".join(text_parts).strip()
    except (KeyError, TypeError) as exc:
        logger.warning("Claude returned unexpected shape: %s", data)
        raise ClaudeUnavailable(f"shape: {exc}") from exc

    if not text:
        logger.warning(
            "Claude returned no text (stop_reason=%s): %s",
            data.get("stop_reason"),
            data,
        )
        raise ClaudeUnavailable(
            f"empty response (stop_reason={data.get('stop_reason')!r})"
        )

    return text
