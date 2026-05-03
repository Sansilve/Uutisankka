"""
LLM-based article category + tone classifier.

Classifies each article into at most 2 categories from a fixed allowed list,
and determines the emotional tone of the article.

Confidence thresholds (configurable in config.py or .env):
  CLASSIFIER_PRIMARY_MIN_CONFIDENCE   — primary category dropped below this (default 0.6)
  CLASSIFIER_SECONDARY_MIN_CONFIDENCE — secondary category dropped below this (default 0.5)
  CLASSIFIER_TONE_MIN_CONFIDENCE      — tone falls back to "neutral" below this (default 0.6)
"""

import json
import logging
import re
from dataclasses import dataclass, field

from ..config import (
    CLASSIFIER_PRIMARY_MIN_CONFIDENCE,
    CLASSIFIER_SECONDARY_MIN_CONFIDENCE,
    CLASSIFIER_TONE_MIN_CONFIDENCE,
    FALLBACK_LLM_API_KEY,
    GEMINI_API_KEY,
    OPENAI_API_KEY,
)
from .llm import LLMUnavailable, chat_with_fallback

log = logging.getLogger(__name__)

ALLOWED_CATEGORIES: frozenset[str] = frozenset(
    [
        "technology",
        "business",
        "politics",
        "sports",
        "weather",
        "culture",
        "science",
        "health",
    ]
)

ALLOWED_TONES: frozenset[str] = frozenset(["positive", "neutral", "negative", "mixed"])

_SYSTEM_PROMPT = """\
You are a strict news classifier.

=== TASK 1: CATEGORY ===

Classify the following article into at most 2 categories from the allowed list.

Rules:
* You MUST choose 1 primary category.
* You MAY choose 1 secondary category only if clearly relevant.
* Do NOT select more than 2 categories.
* Do NOT guess. If unsure, choose the closest match.
* Ignore single keyword matches (e.g. "cloud" does NOT automatically mean weather).
* Focus on the overall topic of the article, not isolated words.
* Prefer high-level meaning over literal word matching.
* If SOURCE or URL clearly indicates a category (e.g. /weather/, /tech/), use it as a strong signal but NOT blindly.

Allowed categories:
["technology", "business", "politics", "sports", "weather", "culture", "science", "health"]

=== TASK 2: TONE ===

Classify the emotional tone of the article based on its dominant message.

Definitions:
* "positive":  Uplifting, heartwarming, or inspiring content. Examples: rescued animals, acts of kindness, happy outcomes, human interest stories.
* "negative":  Content involving harm, violence, war, crime, death, or suffering. Includes serious threats or fear-inducing situations.
* "neutral":   Informational or factual content without strong emotional charge. Examples: business reports, tech updates, general news.
* "mixed":     Contains both positive and negative elements, but neither clearly dominates.

Additional tone rules:
* Focus on the overall narrative, not isolated sentences.
* Do NOT classify as "positive" just because of a single happy detail.
* Do NOT classify as "negative" just because of a single negative word.
* If unsure between two tones, choose "neutral".
* Prefer "negative" if the article centers around harm or conflict.

Allowed tones: ["positive", "neutral", "negative", "mixed"]

=== OUTPUT ===

Return ONLY valid JSON in this format (no markdown, no code fences, no extra text):
{
  "primary": "category_name",
  "secondary": ["optional_second_category"],
  "confidence": {
    "primary": 0.0,
    "secondary": 0.0
  },
  "tone": "tone_value",
  "tone_confidence": 0.0,
  "tone_reason": "one short sentence explaining tone choice"
}\
"""

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
_LLM_AVAILABLE = bool(OPENAI_API_KEY or FALLBACK_LLM_API_KEY or GEMINI_API_KEY)


@dataclass
class ClassificationResult:
    primary: str
    secondary: str | None = None
    primary_confidence: float = 1.0
    secondary_confidence: float = 0.0
    tone: str = "neutral"
    tone_confidence: float = 0.0
    tone_reason: str | None = None


def _parse_response(raw: str) -> ClassificationResult | None:
    """Parse LLM JSON response into ClassificationResult. Returns None on failure."""
    match = _JSON_RE.search(raw)
    if not match:
        return None
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return None

    primary = (data.get("primary") or "").strip().lower()
    if primary not in ALLOWED_CATEGORIES:
        return None

    confidence = data.get("confidence") or {}
    primary_conf = float(confidence.get("primary") or 1.0)
    if primary_conf < CLASSIFIER_PRIMARY_MIN_CONFIDENCE:
        log.debug("classifier: primary '%s' confidence %.2f below threshold — dropped", primary, primary_conf)
        return None

    secondary: str | None = None
    secondary_conf = float(confidence.get("secondary") or 0.0)
    raw_secondary = data.get("secondary") or []
    if isinstance(raw_secondary, list) and raw_secondary:
        candidate = raw_secondary[0].strip().lower()
        if (
            candidate in ALLOWED_CATEGORIES
            and candidate != primary
            and secondary_conf >= CLASSIFIER_SECONDARY_MIN_CONFIDENCE
        ):
            secondary = candidate

    # --- tone ---
    raw_tone = (data.get("tone") or "neutral").strip().lower()
    tone_conf = float(data.get("tone_confidence") or 0.0)
    tone_reason: str | None = (data.get("tone_reason") or "").strip() or None

    # Stabilise: low-confidence tone falls back to neutral
    if raw_tone not in ALLOWED_TONES or tone_conf < CLASSIFIER_TONE_MIN_CONFIDENCE:
        raw_tone = "neutral"
        tone_conf = 0.0
        tone_reason = None

    return ClassificationResult(
        primary=primary,
        secondary=secondary,
        primary_confidence=primary_conf,
        secondary_confidence=secondary_conf if secondary else 0.0,
        tone=raw_tone,
        tone_confidence=tone_conf,
        tone_reason=tone_reason,
    )


def _validator(text: str) -> bool:
    """Validator passed to chat_with_fallback — True if parseable."""
    return _parse_response(text) is not None


def classify_article(
    title: str,
    content: str,
    source: str,
    url: str,
) -> ClassificationResult | None:
    """
    Classify article using LLM: up to 2 categories + emotional tone.

    Returns ClassificationResult or None if LLM unavailable / primary confidence too low.
    Never raises — caller can always treat None as 'unclassified'.
    """
    if not _LLM_AVAILABLE:
        return None

    user_text = (
        f"TITLE: {title}\n"
        f"CONTENT: {content[:1500]}\n"
        f"SOURCE: {source}\n"
        f"URL: {url}"
    )
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]

    try:
        raw = chat_with_fallback(
            messages,
            max_tokens=250,
            temperature=0.1,
            validator=_validator,
        )
        result = _parse_response(raw)
        if result:
            log.debug(
                "classifier: '%s' → primary=%s(%.2f) secondary=%s tone=%s(%.2f)",
                title[:60],
                result.primary,
                result.primary_confidence,
                result.secondary,
                result.tone,
                result.tone_confidence,
            )
        return result
    except LLMUnavailable as exc:
        log.debug("classifier: LLM unavailable — %s", exc)
        return None

    except LLMUnavailable as exc:
        log.debug("classifier: LLM unavailable — %s", exc)
        return None
