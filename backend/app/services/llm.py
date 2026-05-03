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
from typing import Callable, Protocol

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
    PROVIDER_TIMEOUT_SECONDS,
)

log = logging.getLogger(__name__)


class LLMUnavailable(Exception):
    """Raised when all LLM providers have failed or are unconfigured."""


class LLMProvider(Protocol):
    """Provider contract for chat-based LLM backends."""

    name: str

    def is_available(self) -> bool:
        """Return True when provider has the required runtime configuration."""

    def chat(
        self,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Return model output as plain text."""


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
        _primary = OpenAI(
            api_key=OPENAI_API_KEY,
            max_retries=0,
            timeout=PROVIDER_TIMEOUT_SECONDS["openai"],
        )
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
            timeout=PROVIDER_TIMEOUT_SECONDS["fallback"],
        )
    return _fallback


def _get_gemini():
    """Return a Gemini Client, or None if unavailable."""
    if not GEMINI_API_KEY or genai is None:
        return None
    global _gemini
    if _gemini is None:
        _gemini = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=genai.types.HttpOptions(
                timeout=max(1, int(PROVIDER_TIMEOUT_SECONDS["gemini"])),
            ),
        )
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


class OpenAIProvider:
    name = "openai"

    def is_available(self) -> bool:
        return _get_primary() is not None

    def chat(self, messages: list[dict], max_tokens: int, temperature: float) -> str:
        client = _get_primary()
        if client is None:
            raise LLMUnavailable("OpenAI client unavailable")
        return _call_openai_like(
            client=client,
            model=LLM_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            provider_name=self.name,
            max_rps=LLM_MAX_RPS_OPENAI,
        )


class FallbackOpenAIProvider:
    name = "fallback"

    def is_available(self) -> bool:
        return _get_fallback() is not None

    def chat(self, messages: list[dict], max_tokens: int, temperature: float) -> str:
        client = _get_fallback()
        if client is None:
            raise LLMUnavailable("Fallback client unavailable")
        return _call_openai_like(
            client=client,
            model=FALLBACK_LLM_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            provider_name=self.name,
            max_rps=LLM_MAX_RPS_FALLBACK,
        )


class GeminiProvider:
    name = "gemini"

    def is_available(self) -> bool:
        return _get_gemini() is not None

    def chat(self, messages: list[dict], max_tokens: int, temperature: float) -> str:
        return _call_gemini(messages=messages, max_tokens=max_tokens, temperature=temperature)


_provider_registry: dict[str, LLMProvider] = {
    "openai": OpenAIProvider(),
    "fallback": FallbackOpenAIProvider(),
    "gemini": GeminiProvider(),
}

_metrics_lock = threading.Lock()
_llm_metrics: dict[str, dict[str, int | float | list[float]]] = {}


def _ensure_metrics(provider: str) -> dict[str, int | float | list[float]]:
    bucket = _llm_metrics.get(provider)
    if bucket is None:
        bucket = {
            "calls": 0,
            "successes": 0,
            "failures": 0,
            "rate_limit_count": 0,
            "latencies_ms": [],
        }
        _llm_metrics[provider] = bucket
    return bucket


def _is_rate_limit_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True
    text = str(exc).lower()
    return "429" in text or "rate limit" in text


def _record_metric(
    provider: str,
    success: bool,
    elapsed_ms: float,
    rate_limited: bool = False,
) -> None:
    with _metrics_lock:
        bucket = _ensure_metrics(provider)
        bucket["calls"] += 1
        if success:
            bucket["successes"] += 1
        else:
            bucket["failures"] += 1
        if rate_limited:
            bucket["rate_limit_count"] += 1
        latencies = bucket["latencies_ms"]
        if isinstance(latencies, list):
            latencies.append(elapsed_ms)


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((len(ordered) - 1) * p))
    return ordered[idx]


def get_llm_stats() -> dict[str, dict[str, int | float]]:
    """Return per-provider LLM metrics for admin/observability endpoints."""
    with _metrics_lock:
        provider_names = set(_provider_registry.keys()) | set(_llm_metrics.keys())
        stats: dict[str, dict[str, int | float]] = {}
        for provider in sorted(provider_names):
            bucket = _ensure_metrics(provider)
            latencies = bucket["latencies_ms"]
            latency_values = latencies if isinstance(latencies, list) else []
            stats[provider] = {
                "calls": int(bucket["calls"]),
                "successes": int(bucket["successes"]),
                "failures": int(bucket["failures"]),
                "rate_limit_count": int(bucket["rate_limit_count"]),
                "p50_ms": round(_percentile(latency_values, 0.50), 2),
                "p95_ms": round(_percentile(latency_values, 0.95), 2),
            }
        return stats


def _count_bullets(raw: str) -> int:
    return sum(
        1
        for line in raw.splitlines()
        if line.strip().startswith(("-", "•", "*", "–"))
    )


def _normalize_text(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def validate_llm_response(
    raw: str,
    min_bullets: int = 1,
    input_text: str | None = None,
) -> tuple[bool, str]:
    """Validate raw LLM output before it is accepted for downstream use."""
    if not raw or not raw.strip():
        return False, "empty_response"

    if input_text and _normalize_text(raw) == _normalize_text(input_text):
        return False, "echo_response"

    if min_bullets > 0:
        bullets = _count_bullets(raw)
        if bullets < min_bullets:
            return False, f"insufficient_bullets:{bullets}<{min_bullets}"

    return True, "ok"


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
    fallback_provider = _provider_registry.get("fallback")
    if fallback_provider is not None and fallback_provider.is_available():
        available.append("fallback")
    gemini_provider = _provider_registry.get("gemini")
    if gemini_provider is not None and gemini_provider.is_available():
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
    validator: Callable[[str], tuple[bool, str] | bool] | None = None,
) -> str:
    """Call LLM providers with throttled queueing and latency-aware skipping.

    Default mode (premium=False): actively rotate low-cost providers first
    (fallback/gemini), then OpenAI as a final safety net.

    Premium mode (premium=True): OpenAI first, then low-cost providers.
    
    Smart skipping: providers with P95 latency > threshold are skipped to avoid cascades.
    
    Raises LLMUnavailable if all providers fail or are unconfigured.
    Returns the raw response text string.
    """
    from ..config import PROVIDER_P95_SKIP_THRESHOLD_MS
    
    low_cost = _low_cost_order()

    provider_order: list[str]
    if premium:
        provider_order = ["openai", *low_cost]
    else:
        provider_order = [*low_cost, "openai"]

    tried_any = False
    for provider_name in provider_order:
        provider = _provider_registry.get(provider_name)
        if provider is None or not provider.is_available():
            continue
        
        # Skip provider if P95 latency is too high
        stats = get_llm_stats()
        provider_stats = stats.get(provider_name, {})
        p95_ms = provider_stats.get("p95_ms", 0.0)
        if p95_ms > PROVIDER_P95_SKIP_THRESHOLD_MS:
            log.debug("skip provider %s: P95 latency %.0fms exceeds threshold %.0fms", 
                     provider_name, p95_ms, PROVIDER_P95_SKIP_THRESHOLD_MS)
            continue

        tried_any = True
        started = time.monotonic()
        try:
            text = provider.chat(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if text:
                if validator is not None:
                    validation_result = validator(text)
                    if isinstance(validation_result, tuple):
                        is_valid, reason = validation_result
                    else:
                        is_valid, reason = bool(validation_result), "validator_rejected"

                    if not is_valid:
                        log.warning("llm: %s rejected response (%s)", provider_name, reason)
                        _record_metric(
                            provider=provider_name,
                            success=False,
                            elapsed_ms=(time.monotonic() - started) * 1000.0,
                        )
                        continue

                if provider_name != "openai":
                    log.info("llm: %s used successfully", provider_name)
                _record_metric(
                    provider=provider_name,
                    success=True,
                    elapsed_ms=(time.monotonic() - started) * 1000.0,
                )
                return text
        except TimeoutError as exc:
            log.warning("llm: %s timed out (%s)", provider_name, exc)
            _record_metric(
                provider=provider_name,
                success=False,
                elapsed_ms=(time.monotonic() - started) * 1000.0,
            )
        except (OpenAIError, GoogleAPICallError, Exception) as exc:
            log.warning("llm: %s failed (%s)", provider_name, exc)
            _record_metric(
                provider=provider_name,
                success=False,
                elapsed_ms=(time.monotonic() - started) * 1000.0,
                rate_limited=_is_rate_limit_error(exc),
            )

    if not tried_any:
        raise LLMUnavailable("No LLM provider configured")

    raise LLMUnavailable("No LLM provider available")
