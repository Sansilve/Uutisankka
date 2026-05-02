import hashlib
import html
import json
import re
from datetime import timezone
from difflib import SequenceMatcher
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import feedparser

from ..config import DEFAULT_FEEDS, FEED_REGIONS
from ..database import (
    article_exists_with_hash,
    batch_fetch_feedback_scores,
    batch_update_scores,
    fetch_articles_by_topics,
    fetch_unenriched,
    fetch_unscored,
    fetch_untranslated_english,
    get_article_feedback_score,
    get_preferences,
    insert_article,
    recent_titles,
    update_article_enrichment,
    update_article_score_only,
    update_article_title,
)
from .scoring import score_article
from .summarizer import summarize_article
from .translator import is_english_url, translate_and_summarize, translate_title


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


_PAYWALL_FEED_KEYWORDS = [
    "tilaajille", "vain tilaajille", "subscribers only", "premium",
]


def _is_feed_paywall(entry: Any, content: str) -> bool:
    """Detect paywall from RSS entry tags or content keywords."""
    # Check feedparser tags list
    tags = entry.get("tags") or []
    for tag in tags:
        term = (tag.get("term") or "").lower()
        if any(w in term for w in _PAYWALL_FEED_KEYWORDS):
            return True
    # Check content text
    content_lower = content.lower()
    if any(w in content_lower for w in _PAYWALL_FEED_KEYWORDS):
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
                "region": FEED_REGIONS.get(url, "suomi"),
                "is_paywall_hint": _is_feed_paywall(entry, content),
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
    """Generate summaries for new articles, then score anything unscored."""
    preferences = get_preferences()
    count = 0

    # Step 1: summarise articles that have no summary yet
    for row in fetch_unenriched(limit=300):
        url = row["url"] or ""
        content = row["content"] or ""

        if is_english_url(url):
            # One LLM call: translate title to Finnish + produce Finnish bullets
            finnish_title, summary = translate_and_summarize(row["title"], content)
        else:
            finnish_title = None
            summary = summarize_article(row["title"], content, row["source"])

        # Score using the (potentially translated) title for better Finnish keyword matching
        score_title = finnish_title or row["title"]
        base_score, topics, breakdown_items = score_article(
            title=score_title,
            content=content,
            source=row["source"],
            published_at=row["published_at"],
            preferences=preferences,
        )
        feedback_score = get_article_feedback_score(row["id"])
        total_score = round(base_score + feedback_score, 2)
        update_article_enrichment(
            row["id"], base_score, total_score, topics, summary,
            {"items": breakdown_items}, translated_title=finnish_title,
        )
        count += 1

    # Step 2: score any articles that have a summary but score=0 (e.g. after reset)
    count += rescore_all(preferences)
    return count


def translate_existing_english() -> int:
    """Translate titles of already-enriched English articles that are still in English.
    Runs once after a backend upgrade; safe to call multiple times (idempotent-ish)."""
    from ..database import _conn
    conn = _conn()
    all_urls = [r["url"] for r in conn.execute("SELECT url FROM articles").fetchall()]
    conn.close()

    english_urls = [u for u in all_urls if u and is_english_url(u)]
    rows = fetch_untranslated_english(english_urls)
    if not rows:
        return 0

    count = 0
    for row in rows:
        finnish_title = translate_title(row["title"])
        if finnish_title and finnish_title != row["title"]:
            update_article_title(row["id"], finnish_title)
            count += 1
    return count


def rescore_all(preferences: dict | None = None) -> int:
    """Re-score all articles with base_score=0. Pure Python scoring, no LLM, single DB transaction."""
    if preferences is None:
        preferences = get_preferences()
    rows = fetch_unscored(limit=5000)
    if not rows:
        return 0

    # Fetch all feedback scores in ONE query instead of one per article
    feedback_scores = batch_fetch_feedback_scores()

    # Score all articles in memory
    updates: list[tuple] = []
    for row in rows:
        base_score, topics, breakdown_items = score_article(
            title=row["title"],
            content=row["content"] or "",
            source=row["source"],
            published_at=row["published_at"],
            preferences=preferences,
        )
        feedback_score = feedback_scores.get(row["id"], 0.0)
        total_score = round(base_score + feedback_score, 2)
        updates.append((
            base_score,
            total_score,
            json.dumps(topics),
            json.dumps({"items": breakdown_items}),
            row["id"],
        ))

    # Write everything in a single transaction
    return batch_update_scores(updates)


def rescore_for_topics(changed_topics: list[str], preferences: dict | None = None) -> int:
    """Targeted rescore: only articles that contain ANY of the changed topics.

    Uses fetch_articles_by_topics() as an inverted index lookup so we skip
    all articles that cannot be affected by the preference change.
    No DB reset — existing scores for unaffected articles remain intact.
    Single batch transaction for all writes.
    """
    if not changed_topics:
        return 0
    if preferences is None:
        preferences = get_preferences()

    # Inverted-index lookup: O(n) scan but <5ms for thousands of rows
    rows = fetch_articles_by_topics(changed_topics)
    if not rows:
        return 0

    updates: list[tuple] = []
    for row in rows:
        base_score, topics, breakdown_items = score_article(
            title=row["title"],
            content=row["content"] or "",
            source=row["source"],
            published_at=row["published_at"],
            preferences=preferences,
        )
        feedback_score = float(row["feedback_score"] or 0.0)  # already fetched, no extra query
        total_score = round(base_score + feedback_score, 2)
        updates.append((
            base_score,
            total_score,
            json.dumps(topics),
            json.dumps({"items": breakdown_items}),
            row["id"],
        ))

    return batch_update_scores(updates)
