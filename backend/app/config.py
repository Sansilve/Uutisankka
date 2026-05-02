import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from backend/ directory if present
load_dotenv(BASE_DIR / ".env")

DB_PATH = BASE_DIR / "news.db"

# LLM settings (OpenAI)
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")


def _parse_csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "")
    if not raw.strip():
        return []
    return [value.strip() for value in raw.split(",") if value.strip()]


DEFAULT_CORS_ALLOW_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "http://localhost:8082",
    "http://127.0.0.1:8082",
]

# Example: CORS_ALLOW_ORIGINS=http://localhost:5173,http://192.168.10.50:8081
CORS_ALLOW_ORIGINS: list[str] = _parse_csv_env("CORS_ALLOW_ORIGINS") or DEFAULT_CORS_ALLOW_ORIGINS

# Allows local network clients by default (192.168.x.x). Can be overridden from env.
CORS_ALLOW_ORIGIN_REGEX: str = os.getenv(
    "CORS_ALLOW_ORIGIN_REGEX",
    r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+)(:\d+)?$",
)

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
    "https://www.verkkouutiset.fi/feed/": "suomi",
    "https://www.uusisuomi.fi/feed/": "suomi",
    "https://www.maaseuduntulevaisuus.fi/rss": "suomi",
    # Finland national – English
    "https://finlandtoday.fi/feed": "suomi",
    "https://helsinkitimes.fi/?format=feed": "suomi",
    # Finland national – Finnish
    "https://ku.fi/feed": "suomi",
    "https://aamuposti.fi/feed/rss": "suomi",
    # Finland economy
    "https://www.kauppalehti.fi/rss/etusivu": "suomi",
    "https://www.talouselama.fi/rss/tuoreimmat": "suomi",
    "https://www.arvopaperi.fi/rss/tuoreimmat": "suomi",
    # Finland tech
    "https://www.mikrobitti.fi/rss": "suomi",
    "https://www.tekniikkatalous.fi/rss/tuoreimmat": "suomi",
    # Local: Tampere
    "https://www.aamulehti.fi/rss/tuoreimmat.xml": "paikalliset:tampere",
    "https://feeds.yle.fi/uutiset/rss/yle-pirkanmaa.rss": "paikalliset:tampere",
    # Local: Jyväskylä
    "https://ksml.fi/feed/rss": "paikalliset:jyvaskyla",
    "https://feeds.yle.fi/uutiset/rss/yle-keski-suomi.rss": "paikalliset:jyvaskyla",
    # Local: Kuopio
    "https://savonsanomat.fi/feed/rss": "paikalliset:kuopio",
    "https://feeds.yle.fi/uutiset/rss/yle-savo.rss": "paikalliset:kuopio",
    # Local: Hämeenlinna
    "https://hameensanomat.fi/feed/rss": "paikalliset:hameenlinna",
    "https://feeds.yle.fi/uutiset/rss/yle-hame.rss": "paikalliset:hameenlinna",
    # Local: Lappeenranta
    "https://esaimaa.fi/feed/rss": "paikalliset:lappeenranta",
    "https://feeds.yle.fi/uutiset/rss/yle-etela-karjala.rss": "paikalliset:lappeenranta",
    # Local: Oulu
    "https://www.kaleva.fi/rss/uutiset": "paikalliset:oulu",
    "https://feeds.yle.fi/uutiset/rss/yle-oulu.rss": "paikalliset:oulu",
    "https://feeds.yle.fi/uutiset/rss/yle-lappi.rss": "paikalliset:oulu",
    "https://feeds.yle.fi/uutiset/rss/yle-pohjanmaa.rss": "paikalliset:oulu",
    # Local: Turku
    "https://www.satakunnankansa.fi/rss/tuoreimmat.xml": "paikalliset:turku",
    "https://feeds.yle.fi/uutiset/rss/yle-lounainen-suomi.rss": "paikalliset:turku",
    # Local: Helsinki
    "https://feeds.yle.fi/uutiset/rss/yle-uusimaa.rss": "paikalliset:helsinki",
    "https://uusimaa.fi/feed/rss": "paikalliset:helsinki",
    # Local: Turku extra
    "https://sss.fi/feed": "paikalliset:turku",
    # International
    "https://feeds.bbci.co.uk/news/world/rss.xml": "maailma",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml": "maailma",
    "https://www.theguardian.com/world/rss": "maailma",
    "https://feeds.washingtonpost.com/rss/world": "maailma",
    "https://www.aljazeera.com/xml/rss/all.xml": "maailma",
    "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best": "maailma",
    "https://www.france24.com/en/rss": "maailma",
    "https://feeds.skynews.com/feeds/rss/world.xml": "maailma",
    "https://www.rfi.fr/en/international/rss": "maailma",
    "https://rss.upi.com/news/tn_int.rss": "maailma",
    "https://rss.dw.com/rdf/rss-en-world": "maailma",
    "https://www.euronews.com/rss": "maailma",
    "https://feeds.npr.org/1004/rss.xml": "maailma",
    "http://rss.cnn.com/rss/edition_world.rss": "maailma",
    "https://feeds.feedburner.com/time/world": "maailma",
    "https://www.latimes.com/world-nation/rss2.0.xml": "maailma",
    "https://www.independent.co.uk/news/world/rss": "maailma",
    "https://www.ft.com/world?format=rss": "maailma",
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
