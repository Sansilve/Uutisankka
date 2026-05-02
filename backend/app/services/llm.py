"""
Shared LLM client with primary → fallback1 → fallback2 → heuristic chain.

Primary      : OpenAI (OPENAI_API_KEY + LLM_MODEL)
Fallback 1   : Any OpenAI-compatible endpoint (FALLBACK_LLM_API_KEY +
               FALLBACK_LLM_BASE_URL + FALLBACK_LLM_MODEL), e.g. Groq.
Fallback 2   : Google Gemini (GEMINI_API_KEY + GEMINI_MODEL)

Usage:
    from .llm import chat_with_fallback, LLMUnavailable

    try:
        text = chat_with_fallback(messages, max_tokens=400)
    except LLMUnavailable:
        # all providers failed — use heuristic
        ...
"""

import logging

from openai import OpenAI, OpenAIError

try:
    import google.genai as genai
    from google.api_core.exceptions import GoogleAPICallError
except ImportError:
    genai = None
    GoogleAPICallError = Exception

from ..config import (
    FALLBACK_LLM_API_KEY,
    FALLBACK_LLM_BASE_URL,
    FALLBACK_LLM_MODEL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
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
_gemini = None


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


def _get_gemini():
    """Return a Gemini Client, or None if unavailable."""
    if not GEMINI_API_KEY or genai is None:
        return None
    global _gemini
    if _gemini is None:
        _gemini = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini


def _messages_for_gemini(messages: list[dict]) -> str:
    """Convert OpenAI messages format to a Gemini-friendly prompt string.
    
    Simply concatenates all messages into a single prompt.
    Gemini SDK handles the rest.
    """
    parts = []
    for msg in messages:
        role = msg.get("role", "").upper()
        content = msg.get("content", "")
        if role == "SYSTEM":
            parts.append(content)
        elif role == "USER":
            parts.append(f"User: {content}")
        elif role == "ASSISTANT":
            parts.append(f"Assistant: {content}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------

def chat_with_fallback(
    messages: list[dict],
    max_tokens: int = 400,
    temperature: float = 0.3,
) -> str:
    """Call LLM providers in sequence: primary → fallback1 → fallback2.
    
    Raises LLMUnavailable if all providers fail or are unconfigured.
    Returns the raw response text string.
    """
    # Try primary (OpenAI)
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
            log.warning("llm: primary failed (%s), trying fallback1", exc)

    # Try fallback1 (OpenAI-compatible, e.g. Groq)
    fallback = _get_fallback()
    if fallback is not None:
        try:
            resp = fallback.chat.completions.create(
                model=FALLBACK_LLM_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            log.info("llm: fallback1 (openai-compatible) used successfully")
            return resp.choices[0].message.content.strip()
        except OpenAIError as exc:
            log.warning("llm: fallback1 also failed (%s), trying fallback2", exc)

    # Try fallback2 (Google Gemini)
    gemini = _get_gemini()
    if gemini is not None:
        try:
            prompt = _messages_for_gemini(messages)
            resp = gemini.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                ),
            )
            log.info("llm: fallback2 (gemini) used successfully")
            return resp.text.strip()
        except (GoogleAPICallError, Exception) as exc:
            log.warning("llm: fallback2 (gemini) also failed (%s)", exc)

    raise LLMUnavailable("No LLM provider available")
