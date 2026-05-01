import math
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from dateutil import parser

from ..config import MAJOR_SOURCES

TOPIC_KEYWORDS = {
    "technology": ["ai", "software", "chip", "tech", "startup", "cyber", "cloud"],
    "politics": ["government", "parliament", "policy", "election", "minister", "president"],
    "economy": ["inflation", "gdp", "market", "interest rate", "economy", "trade", "employment"],
    "geopolitics": ["nato", "ukraine", "russia", "china", "sanctions", "war", "diplomacy"],
    "celebrity": ["celebrity", "reality star", "influencer", "gossip"],
    "entertainment": ["tv show", "movie", "red carpet", "music video"],
}

CLICKBAIT_PATTERNS = [
    r"you won[' ]t believe",
    r"what happened next",
    r"shocking",
    r"this one trick",
    r"goes viral",
    r"must see",
]

LOW_SIGNAL_PATTERNS = [
    r"top\s+\d+",
    r"list of",
    r"watch:|video:",
    r"live updates",
]

BREAKING_HINTS = ["breaking", "urgent", "developing"]


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = parser.parse(value)
    except (ValueError, TypeError):
        try:
            dt = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def detect_topics(text: str) -> list[str]:
    haystack = text.lower()
    topics: list[str] = []
    for topic, words in TOPIC_KEYWORDS.items():
        if any(word in haystack for word in words):
            topics.append(topic)
    return topics


def _recency_boost(published_at: str | None) -> float:
    dt = _parse_time(published_at)
    if not dt:
        return 0.0
    age_hours = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600)
    if age_hours > 48:
        return -1.0
    return max(0.0, 2.0 - math.log1p(age_hours))


def score_article(
    title: str,
    content: str,
    source: str,
    published_at: str | None,
    preferences: dict[str, list[str]],
) -> tuple[float, list[str], list[dict[str, float | str]]]:
    combined = f"{title} {content}".lower()
    topics = detect_topics(combined)

    score = 0.0
    breakdown: list[dict[str, float | str]] = []

    if source in MAJOR_SOURCES:
        score += 1.0
        breakdown.append({"reason": "Major source boost", "points": 1.0})

    topic_weights = {
        "politics": 2.8,
        "technology": 2.4,
        "economy": 2.3,
        "geopolitics": 2.6,
        "celebrity": -2.5,
        "entertainment": -1.6,
    }
    for topic in topics:
        points = topic_weights.get(topic, 0.0)
        if points != 0:
            score += points
            breakdown.append({"reason": f"Topic match: {topic}", "points": points})

    for pattern in CLICKBAIT_PATTERNS:
        if re.search(pattern, combined):
            score -= 3.0
            breakdown.append({"reason": f"Clickbait pattern: {pattern}", "points": -3.0})

    for pattern in LOW_SIGNAL_PATTERNS:
        if re.search(pattern, combined):
            score -= 1.8
            breakdown.append({"reason": f"Low-signal pattern: {pattern}", "points": -1.8})

    if title.count("!") >= 2 or title.isupper():
        score -= 2.0
        breakdown.append({"reason": "Aggressive title penalty", "points": -2.0})

    if any(token in combined for token in BREAKING_HINTS):
        score += 1.2
        breakdown.append({"reason": "Breaking news hint", "points": 1.2})

    interests = set(item.lower() for item in preferences.get("interests", []))
    dislikes = set(item.lower() for item in preferences.get("disliked_topics", []))

    for interest in interests:
        if interest in topics:
            score += 2.0
            breakdown.append({"reason": f"Interest topic boost: {interest}", "points": 2.0})
        if interest in combined:
            score += 0.8
            breakdown.append({"reason": f"Interest text boost: {interest}", "points": 0.8})

    for dislike in dislikes:
        if dislike in topics:
            score -= 3.0
            breakdown.append({"reason": f"Disliked topic penalty: {dislike}", "points": -3.0})
        if dislike in combined:
            score -= 1.0
            breakdown.append({"reason": f"Disliked text penalty: {dislike}", "points": -1.0})

    recency_points = _recency_boost(published_at)
    score += recency_points
    if recency_points != 0:
        breakdown.append({"reason": "Recency adjustment", "points": round(recency_points, 2)})

    return round(score, 2), topics, breakdown
