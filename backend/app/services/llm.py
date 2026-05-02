"""
Shared LLM client with primary → fallback → heuristic chain.

Primary  : OpenAI (OPENAI_API_KEY + LLM_MODEL)
Fallback : Any OpenAI-compatible endpoint (FALLBACK_LLM_API_KEY +
           FALLBACK_LLM_BASE_URL + FALLBACK_LLM_MODEL), e.g. Groq.

Usage:
    from .llm import chat_with_fallback, LLMUnavailable

    try:
        text = chat_with_fallback(messages, max_tokens=400)
    except LLMUnavailable:
        # both providers failed — use heuristic
        ...
"""

import logging

from openai import OpenAI, OpenAIError

from ..config import (
    FALLBACK_LLM_API_KEY,
    FALLBACK_LLM_BASE_URL,
    FALLBACK_LLM_MODEL,
    LLM_MODEL,
    OPENAI_API_KEY,
)

log = logging.getLogger(__name__)


class LLMUnavailable(Exception):
    """Raised when all LLM providers have failed or are unconfigured."""


# ---------------------------------------------------------------------------
# Lazy-initialised clients
# ---------------------------------------------------------------------------

_primary: OpenAI | None = None
_fallback: OpenAI | None = None


def _get_primary() -> OpenAI | None:
    if not OPENAI_API_KEY:
        return None
    global _primary
    if _primary is None:
        _primary = OpenAI(api_key=OPENAI_API_KEY)
    return _primary


def _get_fallback() -> OpenAI | None:
    if not FALLBACK_LLM_API_KEY or not FALLBACK_LLM_BASE_URL:
        return None
    global _fallback
    if _fallback is None:
        _fallback = OpenAI(
            api_key=FALLBACK_LLM_API_KEY,
            base_url=FALLBACK_LLM_BASE_URL,
        )
    return _fallback


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------

def chat_with_fallback(
    messages: list[dict],
    max_tokens: int = 400,
    temperature: float = 0.3,
) -> str:
    """Call the primary LLM; on failure try the fallback; raise LLMUnavailable
    if both are unavailable or both raise OpenAIError.

    Returns the raw response text string.
    """
    primary = _get_primary()
    if primary is not None:
        try:
            resp = primary.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.choices[0].message.content.strip()
        except OpenAIError as exc:
            log.warning("llm: primary failed (%s), trying fallback", exc)

    fallback = _get_fallback()
    if fallback is not None:
        try:
            resp = fallback.chat.completions.create(
                model=FALLBACK_LLM_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            log.info("llm: fallback provider used successfully")
            return resp.choices[0].message.content.strip()
        except OpenAIError as exc:
            log.warning("llm: fallback also failed (%s)", exc)

    raise LLMUnavailable("No LLM provider available")
