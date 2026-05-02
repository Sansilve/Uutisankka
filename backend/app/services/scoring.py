import math
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from dateutil import parser

from ..config import MAJOR_SOURCES

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

TOPIC_WEIGHTS: dict[str, float] = {
    "politiikka":    2.8,
    "talous":        2.3,
    "teknologia":    2.4,
    "urheilu":       1.5,
    "kulttuuri":     1.2,
    "terveys":       2.0,
    "ympäristö":     1.8,
    "tiede":         1.8,
    "turvallisuus":  2.6,
    "koulutus":      1.5,
    "kansainväliset": 2.5,
    "viihde":       -1.6,
    "celebrity":    -2.5,
    "rikokset":     -0.8,
    "onnettomuudet": -0.5,
    "sää":          -0.5,
}

CLICKBAIT_PATTERNS = [
    r"you won[' ]t believe",
    r"what happened next",
    r"shocking",
    r"this one trick",
    r"goes viral",
    r"must see",
    r"et usko",
    r"hämmästyttävä",
]

LOW_SIGNAL_PATTERNS = [
    r"top\s+\d+",
    r"list of",
    r"watch:|video:",
    r"live updates",
    r"loto(n|ssa|ssa on|tta)",      # Lotto results
    r"oikea rivi",                   # Lotto "right row" result post
    r"arpajaistulokset",
]

BREAKING_HINTS = ["breaking", "urgent", "developing", "juuri nyt", "äskettäin", "tärkeää"]


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

    for topic in topics:
        points = TOPIC_WEIGHTS.get(topic, 0.0)
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

    interests = {item.lower() for item in preferences.get("interests", [])}
    dislikes = {item.lower() for item in preferences.get("disliked_topics", [])}

    for interest in interests:
        if interest in topics:
            score += 2.0
            breakdown.append({"reason": f"Interest topic boost: {interest}", "points": 2.0})
        elif interest in combined:
            score += 0.8
            breakdown.append({"reason": f"Interest text boost: {interest}", "points": 0.8})

    for dislike in dislikes:
        if dislike in topics:
            score -= 3.0
            breakdown.append({"reason": f"Disliked topic penalty: {dislike}", "points": -3.0})
        elif dislike in combined:
            score -= 1.0
            breakdown.append({"reason": f"Disliked text penalty: {dislike}", "points": -1.0})

    recency_points = _recency_boost(published_at)
    score += recency_points
    if recency_points != 0:
        breakdown.append({"reason": "Recency adjustment", "points": round(recency_points, 2)})

    return round(score, 2), topics, breakdown

