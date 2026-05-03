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
import threading
import time

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
    LLM_MAX_RPS_FALLBACK,
    LLM_MAX_RPS_GEMINI,
    LLM_MAX_RPS_OPENAI,
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

# Serialize LLM traffic and enforce per-provider request spacing.
_queue_lock = threading.Lock()
_next_allowed_ts: dict[str, float] = {}

# Round-robin cursor for low-cost providers (fallback/gemini).
_rotation_lock = threading.Lock()
_rotation_cursor = 0


def _get_primary() -> OpenAI | None:
    if not OPENAI_API_KEY:
        return None
    global _primary
    if _primary is None:
        # Fail fast on 429/5xx so we can switch provider instead of sleeping.
        _primary = OpenAI(api_key=OPENAI_API_KEY, max_retries=0)
    return _primary


def _get_fallback() -> OpenAI | None:
    if not FALLBACK_LLM_API_KEY or not FALLBACK_LLM_BASE_URL:
        return None
    global _fallback
    if _fallback is None:
        # Fail fast on 429/5xx so rotation can continue immediately.
        _fallback = OpenAI(
            api_key=FALLBACK_LLM_API_KEY,
            base_url=FALLBACK_LLM_BASE_URL,
            max_retries=0,
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


def _throttle(provider: str, max_rps: float) -> None:
    if max_rps <= 0:
        max_rps = 0.1
    min_interval = 1.0 / max_rps
    with _queue_lock:
        now = time.monotonic()
        next_allowed = _next_allowed_ts.get(provider, 0.0)
        wait = max(0.0, next_allowed - now)
        if wait > 0:
            time.sleep(wait)
        _next_allowed_ts[provider] = time.monotonic() + min_interval


def _low_cost_order() -> list[str]:
    available: list[str] = []
    if _get_fallback() is not None:
        available.append("fallback")
    if _get_gemini() is not None:
        available.append("gemini")
    if len(available) <= 1:
        return available

    global _rotation_cursor
    with _rotation_lock:
        start = _rotation_cursor % len(available)
        _rotation_cursor = (_rotation_cursor + 1) % len(available)

    return available[start:] + available[:start]


def _call_openai_like(
    client: OpenAI,
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
    provider_name: str,
    max_rps: float,
) -> str:
    _throttle(provider_name, max_rps)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return (resp.choices[0].message.content or "").strip()


def _call_gemini(
    messages: list[dict],
    max_tokens: int,
    temperature: float,
) -> str:
    gemini = _get_gemini()
    if gemini is None:
        raise LLMUnavailable("Gemini client unavailable")
    _throttle("gemini", LLM_MAX_RPS_GEMINI)
    prompt = _messages_for_gemini(messages)
    resp = gemini.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        ),
    )
    return (resp.text or "").strip()


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------

def chat_with_fallback(
    messages: list[dict],
    max_tokens: int = 400,
    temperature: float = 0.3,
    premium: bool = False,
) -> str:
    """Call LLM providers with throttled queueing.

    Default mode (premium=False): actively rotate low-cost providers first
    (fallback1/gemini), then OpenAI as a final safety net.

    Premium mode (premium=True): OpenAI first, then low-cost providers.
    
    Raises LLMUnavailable if all providers fail or are unconfigured.
    Returns the raw response text string.
    """
    primary = _get_primary()
    fallback = _get_fallback()
    low_cost = _low_cost_order()

    provider_order: list[str]
    if premium:
        provider_order = ["openai", *low_cost]
    else:
        provider_order = [*low_cost, "openai"]

    tried_any = False
    for provider in provider_order:
        if provider == "openai":
            if primary is None:
                continue
            tried_any = True
            try:
                text = _call_openai_like(
                    client=primary,
                    model=LLM_MODEL,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    provider_name="openai",
                    max_rps=LLM_MAX_RPS_OPENAI,
                )
                if text:
                    return text
            except OpenAIError as exc:
                log.warning("llm: openai failed (%s)", exc)
        elif provider == "fallback":
            if fallback is None:
                continue
            tried_any = True
            try:
                text = _call_openai_like(
                    client=fallback,
                    model=FALLBACK_LLM_MODEL,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    provider_name="fallback",
                    max_rps=LLM_MAX_RPS_FALLBACK,
                )
                if text:
                    log.info("llm: fallback1 (openai-compatible) used successfully")
                    return text
            except OpenAIError as exc:
                log.warning("llm: fallback1 failed (%s)", exc)
        elif provider == "gemini":
            if _get_gemini() is None:
                continue
            tried_any = True
            try:
                text = _call_gemini(messages=messages, max_tokens=max_tokens, temperature=temperature)
                if text:
                    log.info("llm: fallback2 (gemini) used successfully")
                    return text
            except (GoogleAPICallError, Exception) as exc:
                log.warning("llm: fallback2 failed (%s)", exc)

    if not tried_any:
        raise LLMUnavailable("No LLM provider configured")

    raise LLMUnavailable("No LLM provider available")
