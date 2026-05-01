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

DEFAULT_FEEDS = [
    # Finland: public service and major general news
    "https://yle.fi/uutiset/rss",
    "https://www.hs.fi/rss/tuoreimmat.xml",
    "https://www.iltalehti.fi/rss/uutiset.xml",
    "https://www.is.fi/rss/tuoreimmat.xml",
    "https://www.aamulehti.fi/rss/tuoreimmat.xml",
    "https://www.satakunnankansa.fi/rss/tuoreimmat.xml",
    "https://www.kaleva.fi/rss/uutiset",
    "https://www.verkkouutiset.fi/feed/",
    "https://www.uusisuomi.fi/feed/",
    "https://www.maaseuduntulevaisuus.fi/rss",

    # Finland: economy and business
    "https://www.kauppalehti.fi/rss/etusivu",
    "https://www.talouselama.fi/rss/tuoreimmat",
    "https://www.arvopaperi.fi/rss/tuoreimmat",

    # Finland: tech
    "https://www.mikrobitti.fi/rss",
    "https://www.tekniikkatalous.fi/rss/tuoreimmat",

    # International
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://www.theguardian.com/world/rss",
    "https://feeds.washingtonpost.com/rss/world",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
]

MAJOR_SOURCES = {
    "Yle Uutiset",
    "Helsingin Sanomat",
    "BBC News",
    "Reuters",
    "The New York Times",
}
