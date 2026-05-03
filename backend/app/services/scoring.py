import math
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from dateutil import parser

from ..config import (
    ADAPTIVE_SCORING_ENABLED,
    AFFINITY_CATEGORY_WEIGHT,
    AFFINITY_EXPLICIT_TOPIC_PRIOR,
    AFFINITY_MIN_SAMPLES,
    AFFINITY_PRIOR_ALPHA,
    AFFINITY_PRIOR_BETA,
    AFFINITY_SIGNAL_MAX_ABS,
    AFFINITY_SOURCE_WEIGHT,
    AFFINITY_TOPIC_WEIGHT,
    BREAKING_HINTS,
    CLICKBAIT_PATTERNS,
    LOW_SIGNAL_PATTERNS,
    MAJOR_SOURCES,
    SCORING_VERSION,
    TOPIC_WEIGHTS,
)

# Keys match the chip IDs in the frontend exactly.
# Each list contains Finnish and English keywords found in article text/titles.
TOPIC_KEYWORDS: dict[str, list[str]] = {
    # --- interest categories ---
    "politiikka": [
        "hallitus", "eduskunta", "ministeri", "presidentti", "puolue", "vaali", "poliitikko",
        "oppositio", "hallituspuolue", "budjetti", "lakiesitys", "äänestys", "koalitio",
        "government", "parliament", "minister", "president", "election", "policy", "senate",
    ],
    "talous": [
        "inflaatio", "bkt", "talous", "kauppa", "markkinat", "korkojen", "työllisyys",
        "vienti", "tuonti", "pörssit", "osakekurssi", "pankki", "lainaa", "verotus",
        "yrittäjä", "yritys", "liikevaihto", "liikevoitto", "liiketappio", "konkurssi",
        "inflation", "gdp", "economy", "market", "interest rate", "trade", "employment",
        "revenue", "profit", "bankruptcy", "stock", "shares", "finance",
    ],
    "teknologia": [
        "tekoäly", "ohjelmisto", "siru", "startup", "kyber", "pilvi", "data",
        "robotti", "sovellus", "älypuhelin", "tietoturva", "digitalisaatio", "koneoppiminen",
        "software", "chip", "tech", "cyber", "cloud", "algorithm", "machine learning",
        "automation", "semiconductor", "quantum", "5g", "blockchain", "artificial intelligence",
    ],
    "urheilu": [
        "jalkapallo", "jääkiekko", "yleisurheilu", "tennis", "koripallo", "pesäpallo",
        "formula", "hiihto", "mm-kisat", "olympia", "liiga", "turnaus", "ottelu", "maajoukkue",
        "voittaja", "mestaruus", "tulospalvelu",
        "football", "hockey", "athletics", "basketball", "formula 1", "championship",
        "tournament", "match", "league", "olympic", "world cup",
    ],
    "kulttuuri": [
        "kulttuuri", "taide", "museo", "teatteri", "kirjallisuus", "kirja", "romaani",
        "elokuva", "musiikki", "konsertti", "festivaali", "näyttely", "palkinto",
        "art", "museum", "theatre", "literature", "book", "film", "movie", "music",
        "concert", "festival", "exhibition", "award",
    ],
    "terveys": [
        "terveys", "sairaala", "lääkäri", "rokote", "pandemia", "epidemia", "virus",
        "hoito", "lääke", "tutkimus", "syöpä", "diabetes", "sydän", "mielenterveys",
        "health", "hospital", "vaccine", "pandemic", "disease", "treatment", "medicine",
        "cancer", "diabetes", "mental health", "surgery", "clinical",
    ],
    "ympäristö": [
        "ilmasto", "ympäristö", "hiilidioksidi", "päästöt", "fossiiliset", "uusiutuva",
        "tuulivoima", "aurinkoenergia", "biodiversiteetti", "luonnon", "saaste", "kierrätys",
        "climate", "environment", "emissions", "fossil", "renewable", "wind energy",
        "solar", "biodiversity", "pollution", "recycling", "carbon",
    ],
    "tiede": [
        "tiede", "tutkimus", "tutkijat", "yliopisto", "löytö", "avaruus", "tähtitiede",
        "biologia", "kemia", "fysiikka", "geologia", "arkeologia",
        "science", "research", "scientists", "university", "discovery", "space",
        "astronomy", "biology", "chemistry", "physics", "geology", "archaeology",
    ],
    "turvallisuus": [
        "turvallisuus", "poliisi", "rikostutkinta", "terrorismi", "sotilas", "puolustus",
        "nato", "armeija", "konflikti", "sota", "hyökkäys", "kyberturvallisuus",
        "security", "police", "terrorism", "military", "defence", "defense", "nato",
        "army", "conflict", "war", "attack", "cybersecurity", "intelligence",
    ],
    "koulutus": [
        "koulutus", "koulu", "yliopisto", "opiskelu", "opiskelija", "opettaja",
        "lukio", "ammattikoulu", "opinto", "tutkinto", "päiväkoti",
        "education", "school", "university", "student", "teacher", "study",
        "degree", "curriculum", "kindergarten", "learning",
    ],
    "kansainväliset": [
        "ukraina", "venäjä", "kiina", "yhdysvallat", "eu", "eurooppa", "pakotteet",
        "diplomatia", "ulkoministeri", "yhdistyneet kansakunnat", "imf", "maailmanpankki",
        "ukraine", "russia", "china", "united states", "sanctions", "diplomacy",
        "united nations", "european union", "geopolitics", "nato summit", "g7", "g20",
    ],
    # --- disliked / negative categories ---
    "viihde": [
        "viihde", "tosi-tv", "realityohjelma", "juorupalsta", "julkisuuden henkilö",
        "celebrity", "reality", "gossip", "entertainment", "tv show", "red carpet",
        "music video", "influencer", "tiktoker",
    ],
    "celebrity": [
        "julkkis", "julkisuuden henkilö", "tähti", "kuuluisuus", "muusikko",
        "näyttelijä", "influencer",
        "celebrity", "reality star", "gossip", "influencer", "famous",
    ],
    "rikokset": [
        "rikos", "murha", "pahoinpitely", "varkaus", "huumeet", "tuomio", "pidätys",
        "crime", "murder", "assault", "theft", "drugs", "conviction", "arrest",
    ],
    "onnettomuudet": [
        "onnettomuus", "kaatui", "tulipalo", "liikenneonnettomuus", "kolari",
        "accident", "crash", "fire", "collision", "disaster",
    ],
    "sää": [
        "sää", "lämpötila", "ennuste", "pakkanen", "lumimyrsky", "helle", "ukkonen",
        "weather", "temperature", "forecast", "storm", "heatwave", "snow", "frost",
    ],
}

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
    return [
        topic
        for topic, words in TOPIC_KEYWORDS.items()
        if any(word in haystack for word in words)
    ]


def _recency_boost(published_at: str | None) -> float:
    dt = _parse_time(published_at)
    if not dt:
        return 0.0
    age_hours = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600)
    if age_hours > 48:
        return -1.0
    return max(0.0, 2.0 - math.log1p(age_hours))


def _adaptive_enabled() -> bool:
    """Adaptive adjustments are active only in v2 and behind feature flag."""
    return SCORING_VERSION == "v2" and ADAPTIVE_SCORING_ENABLED


def _affinity_points(
    positive: float,
    total: float,
    weight: float,
) -> float:
    if total < AFFINITY_MIN_SAMPLES or weight == 0.0:
        return 0.0
    p = (AFFINITY_PRIOR_ALPHA + positive) / (AFFINITY_PRIOR_ALPHA + AFFINITY_PRIOR_BETA + total)
    signal = 2.0 * (p - 0.5)  # [-1, 1]
    points = weight * signal
    return round(max(-AFFINITY_SIGNAL_MAX_ABS, min(AFFINITY_SIGNAL_MAX_ABS, points)), 2)


def score_article(
    title: str,
    content: str,
    source: str,
    published_at: str | None,
    preferences: dict[str, list[str]],
    topic_swipe_stats: dict[str, dict[str, float]] | None = None,
    source_swipe_stats: dict[str, dict[str, float]] | None = None,
    category_swipe_stats: dict[str, dict[str, float]] | None = None,
    category: str | None = None,
    category_secondary: str | None = None,
    paywall_status: str | None = None,
) -> tuple[float, list[str], list[dict[str, float | str]]]:
    combined = f"{title} {content}".lower()
    topics = detect_topics(combined)

    score = 0.0
    breakdown: list[dict[str, float | str]] = []

    if source in MAJOR_SOURCES:
        score += 1.0
        breakdown.append({"reason": "Major source boost", "points": 1.0, "category": "source"})

    for topic in topics:
        points = TOPIC_WEIGHTS.get(topic, 0.0)
        if points != 0:
            score += points
            breakdown.append({"reason": f"Topic match: {topic}", "points": points, "category": "topical"})

    for pattern in CLICKBAIT_PATTERNS:
        if re.search(pattern, combined):
            score -= 3.0
            breakdown.append({"reason": f"Clickbait pattern: {pattern}", "points": -3.0, "category": "quality"})

    for pattern in LOW_SIGNAL_PATTERNS:
        if re.search(pattern, combined):
            score -= 1.8
            breakdown.append({"reason": f"Low-signal pattern: {pattern}", "points": -1.8, "category": "quality"})

    if title.count("!") >= 2 or title.isupper():
        score -= 2.0
        breakdown.append({"reason": "Aggressive title penalty", "points": -2.0, "category": "quality"})

    if any(token in combined for token in BREAKING_HINTS):
        score += 1.2
        breakdown.append({"reason": "Breaking news hint", "points": 1.2, "category": "quality"})

    # Unified affinity model: explicit like/dislike choices are injected as
    # pseudo-observations into the same topic signal as swipe-learned affinity.
    topic_stats: dict[str, dict[str, float]] = {}
    if _adaptive_enabled() and topic_swipe_stats:
        topic_stats = {
            k.lower(): {
                "positive": float(v.get("positive", 0.0)),
                "total": float(v.get("total", 0.0)),
            }
            for k, v in topic_swipe_stats.items()
        }

    interests = {item.lower() for item in preferences.get("interests", [])}
    dislikes = {item.lower() for item in preferences.get("disliked_topics", [])}

    for interest in interests:
        if interest not in topic_stats:
            topic_stats[interest] = {"positive": 0.0, "total": 0.0}
        topic_stats[interest]["positive"] += AFFINITY_EXPLICIT_TOPIC_PRIOR
        topic_stats[interest]["total"] += AFFINITY_EXPLICIT_TOPIC_PRIOR

    for dislike in dislikes:
        if dislike not in topic_stats:
            topic_stats[dislike] = {"positive": 0.0, "total": 0.0}
        topic_stats[dislike]["total"] += AFFINITY_EXPLICIT_TOPIC_PRIOR

    for topic in topics:
        stats = topic_stats.get(topic.lower())
        if not stats:
            continue
        points = _affinity_points(stats["positive"], stats["total"], AFFINITY_TOPIC_WEIGHT)
        if points != 0.0:
            score += points
            breakdown.append({
                "reason": f"Topic affinity: {topic}",
                "points": points,
                "category": "preference",
            })

    if _adaptive_enabled() and source_swipe_stats:
        source_key = source.strip().lower()
        sstats = source_swipe_stats.get(source_key)
        if sstats:
            points = _affinity_points(sstats["positive"], sstats["total"], AFFINITY_SOURCE_WEIGHT)
            if points != 0.0:
                score += points
                breakdown.append({
                    "reason": f"Source affinity: {source}",
                    "points": points,
                    "category": "source",
                })

    if _adaptive_enabled() and category_swipe_stats:
        category_keys = {
            (category or "").strip().lower(),
            (category_secondary or "").strip().lower(),
        }
        for key in category_keys:
            if not key:
                continue
            cstats = category_swipe_stats.get(key)
            if not cstats:
                continue
            points = _affinity_points(cstats["positive"], cstats["total"], AFFINITY_CATEGORY_WEIGHT)
            if points != 0.0:
                score += points
                breakdown.append({
                    "reason": f"Category affinity: {key}",
                    "points": points,
                    "category": "preference",
                })

    recency_points = _recency_boost(published_at)
    score += recency_points
    if recency_points != 0:
        breakdown.append({"reason": "Recency adjustment", "points": round(recency_points, 2), "category": "freshness"})

    if paywall_status == "uncertain":
        from ..config import UNCERTAIN_PAYWALL_SCORE_PENALTY
        score += UNCERTAIN_PAYWALL_SCORE_PENALTY
        breakdown.append({"reason": "Paywall uncertain", "points": UNCERTAIN_PAYWALL_SCORE_PENALTY, "category": "quality"})

    return round(score, 2), topics, breakdown

