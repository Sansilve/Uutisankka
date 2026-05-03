import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from backend/ directory if present
load_dotenv(BASE_DIR / ".env")

DB_PATH = BASE_DIR / "news.db"

# LLM settings — primary (OpenAI)
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

# LLM settings — fallback 1 (any OpenAI-compatible endpoint, e.g. Groq)
# Set FALLBACK_LLM_API_KEY + FALLBACK_LLM_BASE_URL in .env to enable.
# Example (Groq):
#   FALLBACK_LLM_API_KEY=gsk_...
#   FALLBACK_LLM_BASE_URL=https://api.groq.com/openai/v1
#   FALLBACK_LLM_MODEL=llama-3.1-8b-instant
FALLBACK_LLM_API_KEY: str = os.getenv("FALLBACK_LLM_API_KEY", "")
FALLBACK_LLM_BASE_URL: str = os.getenv("FALLBACK_LLM_BASE_URL", "")
FALLBACK_LLM_MODEL: str = os.getenv("FALLBACK_LLM_MODEL", "llama-3.1-8b-instant")

# LLM settings — fallback 2 (Google Gemini)
# Set GEMINI_API_KEY in .env to enable.
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# LLM traffic shaping (queue + throttle per provider)
LLM_MAX_RPS_OPENAI: float = float(os.getenv("LLM_MAX_RPS_OPENAI", "1.0"))
LLM_MAX_RPS_FALLBACK: float = float(os.getenv("LLM_MAX_RPS_FALLBACK", "2.0"))
LLM_MAX_RPS_GEMINI: float = float(os.getenv("LLM_MAX_RPS_GEMINI", "2.0"))

# Pre-filter gate for LLM translation/summarization in ingest pipeline.
TRANSLATION_SCORE_THRESHOLD: float = float(os.getenv("TRANSLATION_SCORE_THRESHOLD", "0.0"))

# Timeout budget in seconds per provider call.
# Override via env vars:
#   PROVIDER_TIMEOUT_OPENAI_SECONDS
#   PROVIDER_TIMEOUT_FALLBACK_SECONDS
#   PROVIDER_TIMEOUT_GEMINI_SECONDS
PROVIDER_TIMEOUT_SECONDS: dict[str, float] = {
    "openai": float(os.getenv("PROVIDER_TIMEOUT_OPENAI_SECONDS", "10")),
    "fallback": float(os.getenv("PROVIDER_TIMEOUT_FALLBACK_SECONDS", "8")),
    "gemini": float(os.getenv("PROVIDER_TIMEOUT_GEMINI_SECONDS", "12")),
}

# Maps feed URL → region tag: "suomi" | "maailma" | "paikalliset:<city>"
FEED_REGIONS: dict[str, str] = {
    # Finland national
    "https://yle.fi/uutiset/rss": "suomi",
    "https://yle.fi/rss/uutiset/paauutiset": "suomi",
    "https://yle.fi/rss/uutiset/tuoreimmat": "suomi",
    "https://yle.fi/rss/urheilu": "suomi",
    "https://www.hs.fi/rss/tuoreimmat.xml": "suomi",
    "https://www.iltalehti.fi/rss/uutiset.xml": "suomi",
    "https://www.is.fi/rss/tuoreimmat.xml": "suomi",
    "https://www.verkkouutiset.fi/rss": "suomi",
    "https://www.uusisuomi.fi/api/feed/v2/rss/us": "suomi",
    "https://www.maaseuduntulevaisuus.fi/feeds/maaseuduntulevaisuus": "suomi",
    # Finland national – English
    "https://finlandtoday.fi/feed": "suomi",
    "https://www.helsinkitimes.fi/?format=feed": "suomi",
    # Finland national – Finnish
    "https://ku.fi/feed": "suomi",
    "https://aamuposti.fi/feed/rss": "suomi",
    # Finland economy
    "https://feeds.kauppalehti.fi/rss/main": "suomi",
    "https://www.talouselama.fi/api/feed/v2/rss/te": "suomi",
    "https://feeds.kauppalehti.fi/rss/topic/arvopaperi": "suomi",
    # Finland tech
    "https://www.mikrobitti.fi/rss": "suomi",
    "https://www.tekniikkatalous.fi/api/feed/v2/rss/tt": "suomi",
    # Local: Tampere
    "https://www.aamulehti.fi/rss/tuoreimmat.xml": "paikalliset:tampere",
    "https://yle.fi/rss/t/18-146831/fi": "paikalliset:tampere",
    # Local: Jyväskylä
    "https://ksml.fi/feed/rss": "paikalliset:jyvaskyla",
    "https://yle.fi/rss/t/18-148148/fi": "paikalliset:jyvaskyla",
    # Local: Kuopio
    "https://savonsanomat.fi/feed/rss": "paikalliset:kuopio",
    "https://yle.fi/rss/t/18-141764/fi": "paikalliset:kuopio",
    # Local: Hämeenlinna
    "https://hameensanomat.fi/feed/rss": "paikalliset:hameenlinna",
    "https://yle.fi/rss/t/18-138727/fi": "paikalliset:hameenlinna",
    # Local: Lappeenranta
    "https://esaimaa.fi/feed/rss": "paikalliset:lappeenranta",
    "https://yle.fi/rss/t/18-141372/fi": "paikalliset:lappeenranta",
    # Local: Oulu
    "https://www.kaleva.fi/rss": "paikalliset:oulu",
    "https://yle.fi/rss/t/18-148154/fi": "paikalliset:oulu",
    "https://yle.fi/rss/t/18-139752/fi": "paikalliset:oulu",
    "https://yle.fi/rss/t/18-148149/fi": "paikalliset:oulu",
    # Local: Turku
    "https://www.satakunnankansa.fi/rss/tuoreimmat.xml": "paikalliset:turku",
    "https://yle.fi/rss/t/18-135507/fi": "paikalliset:turku",
    # Local: Helsinki
    "https://yle.fi/rss/t/18-147345/fi": "paikalliset:helsinki",
    "https://uusimaa.fi/feed/rss": "paikalliset:helsinki",
    # Local: Turku extra
    "https://sss.fi/feed": "paikalliset:turku",
    # International
    "https://feeds.bbci.co.uk/news/world/rss.xml": "maailma",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml": "maailma",
    "https://www.theguardian.com/world/rss": "maailma",
    "https://www.aljazeera.com/xml/rss/all.xml": "maailma",
    "https://www.france24.com/en/rss": "maailma",
    "https://feeds.skynews.com/feeds/rss/world.xml": "maailma",
    "https://www.rfi.fr/en/rss": "maailma",
    "https://rss.upi.com/news/world_news.rss": "maailma",
    "https://rss.dw.com/rdf/rss-en-all": "maailma",
    "https://www.euronews.com/rss": "maailma",
    "https://feeds.npr.org/1004/rss.xml": "maailma",
    "http://rss.cnn.com/rss/edition_world.rss": "maailma",
    "https://feeds.feedburner.com/time/world": "maailma",
    "https://www.latimes.com/rss2.0.xml": "maailma",
    "https://www.independent.co.uk/rss": "maailma",
    "https://www.ft.com/rss/home/international": "maailma",
    "https://globalnews.ca/world/feed/": "maailma",
}

DEFAULT_FEEDS = list(FEED_REGIONS.keys())

# Cities available for local news
LOCAL_CITIES: dict[str, str] = {
    "tampere": "Tampere",
    "oulu": "Oulu",
    "turku": "Turku",
    "helsinki": "Helsinki",
    "jyvaskyla": "Jyväskylä",
    "kuopio": "Kuopio",
    "hameenlinna": "Hämeenlinna",
    "lappeenranta": "Lappeenranta",
}

MAJOR_SOURCES = {
    "Yle Uutiset",
    "Helsingin Sanomat",
    "BBC News",
    "Reuters",
    "The New York Times",
}

TOPIC_WEIGHTS: dict[str, float] = {
    "politiikka": 2.8,
    "talous": 2.3,
    "teknologia": 2.4,
    "urheilu": 1.5,
    "kulttuuri": 1.2,
    "terveys": 2.0,
    "ympäristö": 1.8,
    "tiede": 1.8,
    "turvallisuus": 2.6,
    "koulutus": 1.5,
    "kansainväliset": 2.5,
    "viihde": -1.6,
    "celebrity": -2.5,
    "rikokset": -0.8,
    "onnettomuudet": -0.5,
    "sää": -0.5,
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
    r"loto(n|ssa|ssa on|tta)",
    r"oikea rivi",
    r"arpajaistulokset",
]

BREAKING_HINTS = ["breaking", "urgent", "developing", "juuri nyt", "äskettäin", "tärkeää"]

# Target language for LLM translation (BCP-47 code).
# Changing this in .env is sufficient to switch the translation target.
# Internal use only — no UI exposure.
TRANSLATION_TARGET_LANG: str = os.getenv("TRANSLATION_TARGET_LANG", "fi")

# Human-readable language name for the target language — used in prompts.
_LANG_NAMES: dict[str, str] = {
    "fi": "Finnish",
    "sv": "Swedish",
    "de": "German",
    "en": "English",
    "fr": "French",
    "es": "Spanish",
}
TRANSLATION_TARGET_LANG_NAME: str = _LANG_NAMES.get(TRANSLATION_TARGET_LANG, TRANSLATION_TARGET_LANG)

# ---------------------------------------------------------------------------
# Article category + tone classifier (LLM-based)
# ---------------------------------------------------------------------------
# Minimum confidence required to keep the primary category.  Below this the
# article is stored as uncategorised (category=NULL).
CLASSIFIER_PRIMARY_MIN_CONFIDENCE: float = float(
    os.getenv("CLASSIFIER_PRIMARY_MIN_CONFIDENCE", "0.6")
)

# Minimum confidence required to keep the secondary category.  Below this the
# secondary is dropped but the primary is kept if it passed its own threshold.
CLASSIFIER_SECONDARY_MIN_CONFIDENCE: float = float(
    os.getenv("CLASSIFIER_SECONDARY_MIN_CONFIDENCE", "0.5")
)

# Minimum tone_confidence required to use the LLM-assigned tone.
# Below this the tone is stabilised to "neutral".
CLASSIFIER_TONE_MIN_CONFIDENCE: float = float(
    os.getenv("CLASSIFIER_TONE_MIN_CONFIDENCE", "0.6")
)

# Adaptive scoring feature flag.
# When enabled, topic weights are adjusted based on swipe history.
ADAPTIVE_SCORING_ENABLED: bool = os.getenv("ADAPTIVE_SCORING_ENABLED", "false").lower() == "true"

# Scoring logic version gate.
# v1 = heuristic baseline (no adaptive topic weighting)
# v2 = baseline + adaptive topic weighting from swipe history
SCORING_VERSION: str = os.getenv("SCORING_VERSION", "v1").strip().lower()
if SCORING_VERSION not in {"v1", "v2"}:
    SCORING_VERSION = "v1"

# Minimum swipe count per topic before adaptive adjustment kicks in.
ADAPTIVE_MIN_SWIPES: int = int(os.getenv("ADAPTIVE_MIN_SWIPES", "5"))

# Source quality tiers — governs pre-filter content-length requirements.
# Domains not listed are treated as "medium".
# low-tier sources require LOW_TIER_MIN_CONTENT_LENGTH characters before LLM call.
SOURCE_QUALITY_TIERS: dict[str, str] = {
    # High-tier: major editorial outlets
    "yle.fi": "high",
    "hs.fi": "high",
    "kauppalehti.fi": "high",
    "bbc.co.uk": "high",
    "nytimes.com": "high",
    "theguardian.com": "high",
    "ft.com": "high",
    "reuters.com": "high",
    # Medium-tier: regional / specialised outlets (default, no entry needed)
    # Low-tier: PR wires, aggregators, short-form feeds
    "prwire.fi": "low",
    "businesswire.com": "low",
    "prnewswire.com": "low",
    "globenewswire.com": "low",
    "accesswire.com": "low",
}

# Minimum content length (chars) for low-tier sources before LLM is called.
# Override via env: LOW_TIER_MIN_CONTENT_LENGTH
LOW_TIER_MIN_CONTENT_LENGTH: int = int(os.getenv("LOW_TIER_MIN_CONTENT_LENGTH", "300"))

# Minimum content length for all other sources (existing threshold).
MIN_CONTENT_LENGTH: int = int(os.getenv("MIN_CONTENT_LENGTH", "150"))

# Paywall score thresholds for tri-state classification.
# score >= PAYWALL_SCORE_PAYWALLED_THRESHOLD -> paywalled
# score <= PAYWALL_SCORE_FREE_THRESHOLD      -> free
# otherwise                                  -> uncertain
PAYWALL_SCORE_PAYWALLED_THRESHOLD: float = float(
    os.getenv("PAYWALL_SCORE_PAYWALLED_THRESHOLD", "0.70")
)
PAYWALL_SCORE_FREE_THRESHOLD: float = float(
    os.getenv("PAYWALL_SCORE_FREE_THRESHOLD", "0.30")
)
