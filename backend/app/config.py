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
    # International
    "https://feeds.bbci.co.uk/news/world/rss.xml": "maailma",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml": "maailma",
    "https://www.theguardian.com/world/rss": "maailma",
    "https://feeds.washingtonpost.com/rss/world": "maailma",
    "https://www.aljazeera.com/xml/rss/all.xml": "maailma",
    "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best": "maailma",
}

DEFAULT_FEEDS = list(FEED_REGIONS.keys())

# Cities available for local news
LOCAL_CITIES: dict[str, str] = {
    "tampere": "Tampere",
    "oulu": "Oulu",
    "turku": "Turku",
    "helsinki": "Helsinki",
}

MAJOR_SOURCES = {
    "Yle Uutiset",
    "Helsingin Sanomat",
    "BBC News",
    "Reuters",
    "The New York Times",
}
