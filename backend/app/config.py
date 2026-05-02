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
    "https://www.verkkouutiset.fi/rss": "suomi",
    "https://www.maaseuduntulevaisuus.fi/feeds/maaseuduntulevaisuus": "suomi",
    # Finland national – English
    "https://finlandtoday.fi/feed": "suomi",
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
