"""Tri-state paywall detection using multiple weak signals.

Status classes:
- free
- paywalled
- uncertain

The detector is intentionally conservative and avoids single-signal decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..config import PAYWALL_SCORE_FREE_THRESHOLD, PAYWALL_SCORE_PAYWALLED_THRESHOLD

PaywallStatus = Literal["free", "paywalled", "uncertain"]


@dataclass
class PaywallSignals:
    scrapeFailure: bool
    shortContent: bool
    paywallKeywords: bool
    sourceHint: bool
    structureHint: bool
    possibleTeaser: bool


@dataclass
class PaywallAssessment:
    status: PaywallStatus
    score: float
    signals: PaywallSignals
    reasons: list[str]


_PAYWALL_KEYWORDS = [
    "tilaajille",
    "vain tilaajille",
    "maksullinen",
    "lue koko juttu",
    "jatka lukemista",
    "subscriber",
    "subscribers only",
    "only for subscribers",
    "subscribe",
    "sign in to read",
    "register to read",
    "continue reading",
    "premium",
    "paywall",
    "unlock article",
]

_TEASER_HINTS = [
    "lue lisaa",
    "jatkuu tilaajille",
    "tilaajana saat",
    "continue reading",
    "subscribe to continue",
]

_DEFAULT_SOURCE_PRIORS: dict[str, float] = {
    # Positive prior = more likely paywalled.
    "helsingin sanomat": 0.15,
    "talouselama": 0.10,
    "kauppalehti": 0.10,
    "aamulehti": 0.10,
    # Negative prior = more likely free.
    "yle": -0.10,
    "reuters": -0.10,
    "bbc": -0.10,
}


def _normalize(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _sentence_count(text: str) -> int:
    parts = [p.strip() for p in text.replace("?", ".").replace("!", ".").split(".")]
    return len([p for p in parts if len(p) > 20])


def _content_word_count(text: str) -> int:
    return len([w for w in _normalize(text).split(" ") if w])


def _has_paywall_keywords(text: str) -> bool:
    norm = _normalize(text)
    return any(k in norm for k in _PAYWALL_KEYWORDS)


def _possible_teaser(text: str) -> bool:
    norm = _normalize(text)
    if any(k in norm for k in _TEASER_HINTS):
        return True
    return norm.endswith("...")


def _is_short_content(text: str) -> bool:
    return _content_word_count(text) < 80


def _has_structure_hint(title: str, content: str) -> bool:
    norm_title = _normalize(title)
    norm_content = _normalize(content)
    if not norm_content:
        return True

    sentences = _sentence_count(content)
    words = _content_word_count(content)

    # Content that is mostly title + tiny preview looks suspicious.
    starts_with_title = norm_content.startswith(norm_title[:40]) if norm_title else False
    return (sentences <= 2 and words < 120) or (starts_with_title and words < 100)


def _source_prior(source: str, overrides: dict[str, float] | None = None) -> float:
    source_norm = _normalize(source)
    priors = dict(_DEFAULT_SOURCE_PRIORS)
    if overrides:
        for key, value in overrides.items():
            priors[_normalize(key)] = float(value)

    for hint, prior in priors.items():
        if hint and hint in source_norm:
            return prior
    return 0.0


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def assess_paywall(
    *,
    title: str,
    content: str,
    source: str,
    scrape_failed: bool = False,
    source_overrides: dict[str, float] | None = None,
) -> PaywallAssessment:
    """Assess paywall likelihood with a weighted multi-signal model."""

    short_content = _is_short_content(content)
    paywall_keywords = _has_paywall_keywords(content)
    structure_hint = _has_structure_hint(title, content)
    possible_teaser = _possible_teaser(content)
    src_prior = _source_prior(source, source_overrides)
    source_hint = src_prior != 0.0

    signals = PaywallSignals(
        scrapeFailure=scrape_failed,
        shortContent=short_content,
        paywallKeywords=paywall_keywords,
        sourceHint=source_hint,
        structureHint=structure_hint,
        possibleTeaser=possible_teaser,
    )

    reasons: list[str] = []
    score = 0.0

    # Scrape failure is weak by design: never enough alone.
    if signals.scrapeFailure:
        score += 0.12
        reasons.append("scrape failed (weak signal)")

    if signals.shortContent:
        score += 0.22
        reasons.append("very short content body")

    if signals.paywallKeywords:
        score += 0.36
        reasons.append("paywall keyword or UI cue detected")

    if signals.structureHint:
        score += 0.20
        reasons.append("article structure resembles teaser")

    if signals.possibleTeaser:
        score += 0.18
        reasons.append("teaser-like ending or phrase detected")

    if src_prior > 0:
        score += src_prior
        reasons.append("source prior indicates frequent paywall")
    elif src_prior < 0:
        score += src_prior
        reasons.append("source prior indicates mostly free source")

    # Strong free evidence should lower risk.
    words = _content_word_count(content)
    sentences = _sentence_count(content)
    if words > 220 and sentences >= 4 and not signals.paywallKeywords:
        score -= 0.28
        reasons.append("long coherent article body suggests free content")

    score = _clamp01(score)

    if score >= PAYWALL_SCORE_PAYWALLED_THRESHOLD:
        status: PaywallStatus = "paywalled"
    elif score <= PAYWALL_SCORE_FREE_THRESHOLD:
        status = "free"
    else:
        status = "uncertain"
        reasons.append("signals are mixed; returning uncertain")

    return PaywallAssessment(status=status, score=round(score, 3), signals=signals, reasons=reasons)
