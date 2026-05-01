import hashlib
import html
import re
from datetime import timezone
from difflib import SequenceMatcher
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import feedparser

from ..config import DEFAULT_FEEDS
from ..database import (
    article_exists_with_hash,
    fetch_unenriched,
    get_article_feedback_score,
    get_preferences,
    insert_article,
    recent_titles,
    update_article_enrichment,
)
from .scoring import score_article
from .summarizer import summarize_article


TAG_RE = re.compile(r"<[^>]+>")


def _clean(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(value)
    value = TAG_RE.sub(" ", value)
    return re.sub(r"\s+", " ", value).strip()


def _to_iso(entry: Any) -> str | None:
    struct_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if not struct_time:
        return None
    try:
        from datetime import datetime

        return datetime(*struct_time[:6], tzinfo=timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


def _content_from_entry(entry: Any) -> str:
    if "content" in entry and entry.content:
        return _clean(entry.content[0].value)
    return _clean(entry.get("summary") or entry.get("description"))


def _hash_payload(title: str, content: str) -> str:
    base = f"{title.lower()}::{content.lower()[:800]}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _is_near_duplicate(title: str, existing_titles: list[str]) -> bool:
    title_l = title.lower()
    for prev in existing_titles:
        ratio = SequenceMatcher(a=title_l, b=prev.lower()).ratio()
        if ratio >= 0.92:
            return True
    return False


def ingest_feeds(feed_urls: list[str] | None = None) -> dict[str, int]:
    feeds = feed_urls or DEFAULT_FEEDS
    fetched = 0
    inserted = 0
    duplicates = 0

    titles = recent_titles(limit=300)

    for url in feeds:
        try:
            with urlopen(url, timeout=8) as response:
                payload = response.read()
            parsed = feedparser.parse(payload)
        except (TimeoutError, URLError, OSError):
            # Skip sources that are temporarily unavailable instead of blocking ingestion.
            continue

        for entry in parsed.entries:
            fetched += 1
            title = _clean(entry.get("title"))
            link = entry.get("link")
            source = _clean(parsed.feed.get("title")) or "Unknown Source"
            content = _content_from_entry(entry)

            if not title or not link:
                duplicates += 1
                continue

            content_hash = _hash_payload(title, content)
            if article_exists_with_hash(content_hash) or _is_near_duplicate(title, titles):
                duplicates += 1
                continue

            article = {
                "title": title,
                "source": source,
                "published_at": _to_iso(entry),
                "content": content,
                "url": link,
                "content_hash": content_hash,
            }

            if insert_article(article):
                inserted += 1
                titles.append(title)
            else:
                duplicates += 1

    enriched = enrich_unprocessed_articles()
    return {
        "fetched": fetched,
        "inserted": inserted,
        "duplicates": duplicates,
        "enriched": enriched,
    }


def enrich_unprocessed_articles() -> int:
    preferences = get_preferences()
    rows = fetch_unenriched(limit=300)
    count = 0

    for row in rows:
        base_score, topics, breakdown_items = score_article(
            title=row["title"],
            content=row["content"] or "",
            source=row["source"],
            published_at=row["published_at"],
            preferences=preferences,
        )
        feedback_score = get_article_feedback_score(row["id"])
        total_score = round(base_score + feedback_score, 2)
        summary = summarize_article(row["title"], row["content"] or "")
        update_article_enrichment(
            row["id"],
            base_score,
            total_score,
            topics,
            summary,
            {"items": breakdown_items},
        )
        count += 1

    return count
