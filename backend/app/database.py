import json
import math
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

from .config import DB_PATH

_db_lock = Lock()


def _conn() -> sqlite3.Connection:
    db_path = Path(DB_PATH)
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {row[1] for row in rows}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db() -> None:
    with _db_lock:
        conn = _conn()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    published_at TEXT,
                    content TEXT,
                    url TEXT NOT NULL UNIQUE,
                    content_hash TEXT NOT NULL,
                    base_score REAL DEFAULT 0,
                    feedback_score REAL DEFAULT 0,
                    score REAL DEFAULT 0,
                    topics TEXT DEFAULT '[]',
                    score_breakdown_json TEXT DEFAULT '{"items": []}',
                    summary_json TEXT DEFAULT '{"bullets": []}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_articles_published ON articles (published_at DESC);
                CREATE INDEX IF NOT EXISTS idx_articles_score ON articles (score DESC);
                CREATE INDEX IF NOT EXISTS idx_articles_hash ON articles (content_hash);

                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER PRIMARY KEY CHECK (user_id = 1),
                    interests TEXT NOT NULL,
                    disliked_topics TEXT NOT NULL,
                    news_scope TEXT NOT NULL DEFAULT '["suomi","maailma"]',
                    local_city TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS article_feedback (
                    article_id INTEGER PRIMARY KEY,
                    positive_count INTEGER NOT NULL DEFAULT 0,
                    negative_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS swipe_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER NOT NULL,
                    is_relevant INTEGER NOT NULL,
                    swiped_at TEXT NOT NULL,
                    FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_swipe_history_swiped_at ON swipe_history (swiped_at DESC);
                """
            )
            _ensure_column(conn, "articles", "base_score", "REAL DEFAULT 0")
            _ensure_column(conn, "articles", "feedback_score", "REAL DEFAULT 0")
            _ensure_column(conn, "articles", "score_breakdown_json", "TEXT DEFAULT '{\"items\": []}'")
            _ensure_column(conn, "articles", "region", "TEXT NOT NULL DEFAULT 'suomi'")
            _ensure_column(conn, "articles", "is_paywall", "INTEGER NOT NULL DEFAULT 0")
            _ensure_column(conn, "articles", "category", "TEXT DEFAULT NULL")
            _ensure_column(conn, "articles", "category_secondary", "TEXT DEFAULT NULL")
            _ensure_column(conn, "articles", "tone", "TEXT DEFAULT NULL")
            _ensure_column(conn, "articles", "tone_confidence", "REAL DEFAULT NULL")
            _ensure_column(conn, "articles", "tone_reason", "TEXT DEFAULT NULL")
            _ensure_column(conn, "articles", "trust_score", "REAL DEFAULT NULL")
            _ensure_column(conn, "articles", "bias_score", "INTEGER DEFAULT NULL")
            _ensure_column(conn, "articles", "factual_rating", "TEXT DEFAULT NULL")
            _ensure_column(conn, "articles", "fact_check_status", "TEXT DEFAULT 'unknown'")
            _ensure_column(conn, "user_preferences", "news_scope", "TEXT NOT NULL DEFAULT '[\"suomi\",\"maailma\"]'")
            _ensure_column(conn, "user_preferences", "local_city", "TEXT NOT NULL DEFAULT ''")
            _ensure_column(conn, "user_preferences", "hide_paywall", "INTEGER NOT NULL DEFAULT 1")
            _ensure_column(conn, "user_preferences", "excluded_sources", "TEXT NOT NULL DEFAULT '[]'")
            _ensure_column(conn, "user_preferences", "tone_filter", "TEXT NOT NULL DEFAULT 'all'")
            _ensure_column(conn, "user_preferences", "trust_filter_enabled", "INTEGER NOT NULL DEFAULT 1")
            _ensure_column(conn, "swipe_history", "dwell_ms", "INTEGER DEFAULT NULL")
            conn.commit()
        finally:
            conn.close()


def ensure_default_preferences() -> None:
    default_interests = ["teknologia", "politiikka", "talous"]
    default_dislikes: list[str] = []
    upsert_preferences(default_interests, default_dislikes, only_if_missing=True)


def upsert_preferences(
    interests: list[str],
    disliked_topics: list[str],
    news_scope: list[str] | None = None,
    local_city: str = "",
    hide_paywall: bool = True,
    excluded_sources: list[str] | None = None,
    tone_filter: str = "all",
    only_if_missing: bool = False,
    trust_filter_enabled: bool = True,
) -> None:
    with _db_lock:
        conn = _conn()
        try:
            existing = conn.execute(
                "SELECT user_id FROM user_preferences WHERE user_id = 1"
            ).fetchone()
            if existing and only_if_missing:
                return

            scope = news_scope if news_scope is not None else ["suomi", "maailma"]
            sources = excluded_sources if excluded_sources is not None else []
            valid_tone_filters = {"all", "positive", "neutral_positive", "neutral"}
            tf = tone_filter if tone_filter in valid_tone_filters else "all"
            timestamp = datetime.utcnow().isoformat()
            if existing:
                conn.execute(
                    """
                    UPDATE user_preferences
                    SET interests = ?, disliked_topics = ?, news_scope = ?, local_city = ?, hide_paywall = ?, excluded_sources = ?, tone_filter = ?, trust_filter_enabled = ?, updated_at = ?
                    WHERE user_id = 1
                    """,
                    (json.dumps(interests), json.dumps(disliked_topics), json.dumps(scope), local_city, int(hide_paywall), json.dumps(sources), tf, int(trust_filter_enabled), timestamp),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO user_preferences (user_id, interests, disliked_topics, news_scope, local_city, hide_paywall, excluded_sources, tone_filter, trust_filter_enabled, updated_at)
                    VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (json.dumps(interests), json.dumps(disliked_topics), json.dumps(scope), local_city, int(hide_paywall), json.dumps(sources), tf, int(trust_filter_enabled), timestamp),
                )
            conn.commit()
        finally:
            conn.close()


def get_preferences() -> dict:
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT interests, disliked_topics, news_scope, local_city, hide_paywall, excluded_sources, tone_filter, trust_filter_enabled FROM user_preferences WHERE user_id = 1"
        ).fetchone()
        if not row:
            return {
                "interests": ["politiikka", "teknologia", "talous"],
                "disliked_topics": [],
                "news_scope": ["suomi", "maailma"],
                "local_city": "",
                "hide_paywall": True,
                "excluded_sources": [],
                "tone_filter": "all",
                "trust_filter_enabled": True,
            }
        return {
            "interests": json.loads(row["interests"]),
            "disliked_topics": json.loads(row["disliked_topics"]),
            "news_scope": json.loads(row["news_scope"] or '["suomi","maailma"]'),
            "local_city": row["local_city"] or "",
            "hide_paywall": bool(row["hide_paywall"]),
            "excluded_sources": json.loads(row["excluded_sources"] or '[]'),
            "tone_filter": row["tone_filter"] or "all",
            "trust_filter_enabled": bool(row["trust_filter_enabled"] if row["trust_filter_enabled"] is not None else 1),
        }
    finally:
        conn.close()


def random_briefing(limit: int = 10, region_filters: list[str] | None = None, hide_paywall: bool = False, excluded_sources: list[str] | None = None) -> list:
    """Return *limit* random enriched articles (score > 0), shuffled each call."""
    conn = _conn()
    try:
        params: list = []
        where_region = ""
        if region_filters:
            placeholders = ",".join("?" * len(region_filters))
            where_region = f"AND a.region IN ({placeholders})"
            params.extend(region_filters)

        where_paywall = "AND a.is_paywall = 0" if hide_paywall else ""
        
        where_sources = ""
        if excluded_sources:
            sp = ",".join("?" * len(excluded_sources))
            where_sources = f"AND a.source NOT IN ({sp})"
            params.extend(excluded_sources)

        params.append(limit)
        rows = conn.execute(
            f"""
            SELECT
                a.id, a.title, a.source, a.published_at, a.url,
                a.score, a.base_score, a.feedback_score,
                a.topics, a.summary_json, a.score_breakdown_json,
                a.is_paywall,
                a.trust_score, a.bias_score, a.factual_rating,
                COALESCE(a.fact_check_status, 'unknown') AS fact_check_status,
                COALESCE(f.positive_count, 0) AS feedback_positive,
                COALESCE(f.negative_count, 0) AS feedback_negative
            FROM articles a
            LEFT JOIN article_feedback f ON f.article_id = a.id
            WHERE a.score > 0
              {where_region}
              {where_paywall}
              {where_sources}
            ORDER BY RANDOM()
            LIMIT ?
            """,
            params,
        ).fetchall()
        return rows
    finally:
        conn.close()


def insert_article(article: dict[str, Any]) -> bool:
    with _db_lock:
        conn = _conn()
        try:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO articles (title, source, published_at, content, url, content_hash, region, is_paywall)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article["title"],
                    article["source"],
                    article["published_at"],
                    article["content"],
                    article["url"],
                    article["content_hash"],
                    article.get("region", "suomi"),
                    1 if article.get("is_paywall_hint") else 0,
                ),
            )
            conn.commit()
            return cursor.rowcount == 1
        finally:
            conn.close()


def article_exists_with_hash(content_hash: str, limit_hours: int = 96) -> bool:
    conn = _conn()
    try:
        row = conn.execute(
            """
            SELECT id FROM articles
            WHERE content_hash = ?
            AND datetime(created_at) >= datetime('now', ?)
            LIMIT 1
            """,
            (content_hash, f"-{limit_hours} hours"),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def recent_titles(limit: int = 250) -> list[str]:
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT title FROM articles ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [r["title"] for r in rows]
    finally:
        conn.close()


def fetch_unenriched(limit: int = 200) -> list[sqlite3.Row]:
    """Articles that still need a summary generated."""
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT id, title, source, published_at, content, url, category, category_secondary
            FROM articles
            WHERE summary_json = '{"bullets": []}'
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return rows
    finally:
            return rows


def fetch_untranslated_english(urls: list[str]) -> list[sqlite3.Row]:
    """English-source articles that already have summaries but NOT yet Finnish titles.
    Identified by matching their exact URLs against the given list."""
    if not urls:
        return []
    placeholders = ",".join("?" * len(urls))
    conn = _conn()
    try:
        return conn.execute(
            f"""
            SELECT id, title, content, source, published_at, url
            FROM articles
            WHERE url IN ({placeholders})
              AND summary_json != '{{"bullets": []}}'
            ORDER BY created_at DESC
            """,
            urls,
        ).fetchall()
    finally:
        conn.close()


def update_article_title(article_id: int, title: str) -> None:
    """Update only the title column (used when translating existing articles)."""
    with _db_lock:
        conn = _conn()
        try:
            conn.execute("UPDATE articles SET title = ? WHERE id = ?", (title, article_id))
            conn.commit()
        finally:
            conn.close()


def fetch_unscored(limit: int = 5000) -> list[sqlite3.Row]:
    """Articles that have a summary but need (re-)scoring. Excludes heavy content column."""
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT id, title, source, published_at, content, category, category_secondary
            FROM articles
            WHERE base_score = 0
              AND summary_json != '{"bullets": []}'
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return rows
    finally:
        conn.close()


def batch_fetch_feedback_scores() -> dict[int, float]:
    """Return {article_id: feedback_score} for all articles in one query."""
    conn = _conn()
    try:
        rows = conn.execute("SELECT id, feedback_score FROM articles").fetchall()
        return {row["id"]: float(row["feedback_score"] or 0.0) for row in rows}
    finally:
        conn.close()


def batch_update_scores(updates: list[tuple]) -> int:
    """Write (base_score, score, topics_json, breakdown_json, id) rows in a single transaction.
    Returns number of rows updated."""
    if not updates:
        return 0
    with _db_lock:
        conn = _conn()
        try:
            conn.executemany(
                """
                UPDATE articles
                SET base_score = ?, score = ?, topics = ?, score_breakdown_json = ?
                WHERE id = ?
                """,
                updates,
            )
            conn.commit()
            return len(updates)
        finally:
            conn.close()


def fetch_articles_by_topics(topics: list[str]) -> list[sqlite3.Row]:
    """Return all scored articles that have ANY of the given topics detected.
    Uses SQLite json_each() as an inverted index: O(n) table scan, <5ms for thousands of rows.
    Fetches content too so score_article() can re-run keyword matching.
    """
    if not topics:
        return []
    placeholders = ",".join("?" * len(topics))
    conn = _conn()
    try:
        return conn.execute(
            f"""
            SELECT id, title, content, source, published_at, feedback_score,
                   category, category_secondary
            FROM articles
            WHERE topics IS NOT NULL
              AND topics != '[]'
              AND EXISTS (
                  SELECT 1 FROM json_each(articles.topics)
                  WHERE json_each.value IN ({placeholders})
              )
            """,
            topics,
        ).fetchall()
    finally:
        conn.close()


def reset_all_enrichment() -> int:
    """Reset ONLY scoring fields on all articles — summaries are preserved.
    Returns the number of rows reset."""
    with _db_lock:
        conn = _conn()
        try:
            cursor = conn.execute(
                """
                UPDATE articles
                SET base_score = 0,
                    score = 0,
                    topics = '[]',
                    score_breakdown_json = '{"items": []}'
                """
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()


def get_article_feedback_score(article_id: int) -> float:
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT feedback_score FROM articles WHERE id = ?",
            (article_id,),
        ).fetchone()
        if not row:
            return 0.0
        return float(row["feedback_score"] or 0.0)
    finally:
        conn.close()


def get_topic_swipe_stats() -> dict[str, dict[str, int]]:
    """Return per-topic swipe counts from swipe_history joined with articles.

    Returns:
        {topic: {"positive": int, "total": int}}
    """
    topic_stats, _, _ = get_affinity_swipe_stats()
    return {
        topic: {
            "positive": int(round(values["positive"])),
            "total": int(round(values["total"])),
        }
        for topic, values in topic_stats.items()
    }


def get_affinity_swipe_stats(half_life_days: float = 30.0) -> tuple[
    dict[str, dict[str, float]],
    dict[str, dict[str, float]],
    dict[str, dict[str, float]],
]:
    """Return decayed swipe stats for topic, source and category."""
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT a.topics, a.source, a.category, a.category_secondary,
                   s.is_relevant, s.swiped_at, s.dwell_ms
            FROM swipe_history s
            JOIN articles a ON a.id = s.article_id
            """
        ).fetchall()
    finally:
        conn.close()

    topic_stats: dict[str, dict[str, float]] = {}
    source_stats: dict[str, dict[str, float]] = {}
    category_stats: dict[str, dict[str, float]] = {}

    now = datetime.utcnow()
    safe_half_life = max(1.0, float(half_life_days))

    def _weight(swiped_at: str | None) -> float:
        if not swiped_at:
            return 1.0
        try:
            dt = datetime.fromisoformat(swiped_at.replace("Z", "+00:00"))
            age_days = max(0.0, (now - dt.replace(tzinfo=None)).total_seconds() / 86400.0)
            return math.pow(0.5, age_days / safe_half_life)
        except Exception:
            return 1.0

    def _add(stats: dict[str, dict[str, float]], key: str, is_positive: bool, weight: float) -> None:
        norm = (key or "").strip().lower()
        if not norm:
            return
        if norm not in stats:
            stats[norm] = {"positive": 0.0, "total": 0.0}
        stats[norm]["total"] += weight
        if is_positive:
            stats[norm]["positive"] += weight

    def _dwell_multiplier(dwell_ms: int | None) -> float:
        """Strong signal if user stayed >= DWELL_STRONG_MS; weak if < DWELL_WEAK_MS."""
        from .config import DWELL_STRONG_MS, DWELL_WEAK_MS
        if dwell_ms is None:
            return 1.0
        if dwell_ms >= DWELL_STRONG_MS:
            return 1.5
        if dwell_ms < DWELL_WEAK_MS:
            return 0.7
        return 1.0

    for row in rows:
        is_positive = bool(row["is_relevant"])
        weight = _weight(row["swiped_at"]) * _dwell_multiplier(row["dwell_ms"])

        for topic in json.loads(row["topics"] or "[]"):
            _add(topic_stats, topic, is_positive, weight)

        _add(source_stats, row["source"] or "", is_positive, weight)
        _add(category_stats, row["category"] or "", is_positive, weight)
        _add(category_stats, row["category_secondary"] or "", is_positive, weight)

    return topic_stats, source_stats, category_stats


def update_article_enrichment(
    article_id: int,
    base_score: float,
    total_score: float,
    topics: list[str],
    summary: dict[str, Any],
    score_breakdown: dict[str, Any],
    translated_title: str | None = None,
    category: str | None = None,
    category_secondary: str | None = None,
    tone: str | None = None,
    tone_confidence: float | None = None,
    tone_reason: str | None = None,
    trust_score: float | None = None,
    bias_score: int | None = None,
    factual_rating: str | None = None,
) -> None:
    status = summary.get("paywall_status")
    is_paywall_from_summary = 1 if (summary.get("source") == "no_content" or status == "paywalled") else 0
    with _db_lock:
        conn = _conn()
        try:
            # Recompute from latest summary assessment to avoid sticky false flags.
            is_paywall = is_paywall_from_summary
            if translated_title:
                conn.execute(
                    """
                    UPDATE articles
                    SET title = ?, base_score = ?, score = ?, topics = ?,
                        summary_json = ?, score_breakdown_json = ?, is_paywall = ?,
                        category = ?, category_secondary = ?,
                        tone = ?, tone_confidence = ?, tone_reason = ?,
                        trust_score = ?, bias_score = ?, factual_rating = ?
                    WHERE id = ?
                    """,
                    (
                        translated_title,
                        base_score,
                        total_score,
                        json.dumps(topics),
                        json.dumps(summary),
                        json.dumps(score_breakdown),
                        is_paywall,
                        category,
                        category_secondary,
                        tone,
                        tone_confidence,
                        tone_reason,
                        trust_score,
                        bias_score,
                        factual_rating,
                        article_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE articles
                    SET base_score = ?, score = ?, topics = ?, summary_json = ?,
                        score_breakdown_json = ?, is_paywall = ?,
                        category = ?, category_secondary = ?,
                        tone = ?, tone_confidence = ?, tone_reason = ?,
                        trust_score = ?, bias_score = ?, factual_rating = ?
                    WHERE id = ?
                    """,
                    (
                        base_score,
                        total_score,
                        json.dumps(topics),
                        json.dumps(summary),
                        json.dumps(score_breakdown),
                        is_paywall,
                        category,
                        category_secondary,
                        tone,
                        tone_confidence,
                        tone_reason,
                        trust_score,
                        bias_score,
                        factual_rating,
                        article_id,
                    ),
                )
            conn.commit()
        finally:
            conn.close()


def update_article_score_only(
    article_id: int,
    base_score: float,
    total_score: float,
    topics: list[str],
    score_breakdown: dict[str, Any],
) -> None:
    """Update score/topics/breakdown without touching the summary."""
    with _db_lock:
        conn = _conn()
        try:
            conn.execute(
                """
                UPDATE articles
                SET base_score = ?, score = ?, topics = ?, score_breakdown_json = ?
                WHERE id = ?
                """,
                (
                    base_score,
                    total_score,
                    json.dumps(topics),
                    json.dumps(score_breakdown),
                    article_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()


def apply_feedback(article_id: int, is_relevant: bool, dwell_ms: int | None = None) -> dict[str, float | int]:
    with _db_lock:
        conn = _conn()
        try:
            row = conn.execute(
                """
                SELECT positive_count, negative_count
                FROM article_feedback
                WHERE article_id = ?
                """,
                (article_id,),
            ).fetchone()

            positive = int(row["positive_count"]) if row else 0
            negative = int(row["negative_count"]) if row else 0

            if is_relevant:
                positive += 1
            else:
                negative += 1

            timestamp = datetime.utcnow().isoformat()
            if row:
                conn.execute(
                    """
                    UPDATE article_feedback
                    SET positive_count = ?, negative_count = ?, updated_at = ?
                    WHERE article_id = ?
                    """,
                    (positive, negative, timestamp, article_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO article_feedback (article_id, positive_count, negative_count, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (article_id, positive, negative, timestamp),
                )

            conn.execute(
                """
                INSERT INTO swipe_history (article_id, is_relevant, swiped_at, dwell_ms)
                VALUES (?, ?, ?, ?)
                """,
                (article_id, 1 if is_relevant else 0, timestamp, dwell_ms),
            )

            net_votes = positive - negative
            feedback_score = round(max(-4.0, min(4.0, net_votes * 0.8)), 2)

            article = conn.execute(
                "SELECT base_score FROM articles WHERE id = ?",
                (article_id,),
            ).fetchone()
            base_score = float(article["base_score"] or 0.0) if article else 0.0
            total_score = round(base_score + feedback_score, 2)

            conn.execute(
                """
                UPDATE articles
                SET feedback_score = ?, score = ?
                WHERE id = ?
                """,
                (feedback_score, total_score, article_id),
            )
            conn.commit()

            return {
                "article_id": article_id,
                "feedback_positive": positive,
                "feedback_negative": negative,
                "feedback_score": feedback_score,
                "total_score": total_score,
            }
        finally:
            conn.close()


def top_briefing(limit: int = 10, region_filters: list[str] | None = None, hide_paywall: bool = False, excluded_sources: list[str] | None = None, tone_filter: str = "all") -> list[sqlite3.Row]:
    conn = _conn()
    try:
        params: list = []
        where_region = ""
        if region_filters:
            placeholders = ",".join("?" * len(region_filters))
            where_region = f"AND a.region IN ({placeholders})"
            params.extend(region_filters)

        where_paywall = "AND a.is_paywall = 0" if hide_paywall else ""

        where_sources = ""
        if excluded_sources:
            sp = ",".join("?" * len(excluded_sources))
            where_sources = f"AND a.source NOT IN ({sp})"
            params.extend(excluded_sources)

        where_tone = ""
        if tone_filter == "positive":
            where_tone = "AND (a.tone = 'positive' OR a.tone IS NULL)"
        elif tone_filter == "neutral_positive":
            where_tone = "AND (a.tone IS NULL OR a.tone IN ('positive', 'neutral'))"
        elif tone_filter == "neutral":
            where_tone = "AND (a.tone = 'neutral' OR a.tone IS NULL)"

        params.append(limit)
        return conn.execute(
            f"""
            SELECT
                a.id,
                a.title,
                a.source,
                a.published_at,
                a.url,
                a.score,
                a.base_score,
                a.feedback_score,
                a.topics,
                a.summary_json,
                a.score_breakdown_json,
                a.is_paywall,
                a.category,
                a.category_secondary,
                a.tone,
                a.tone_confidence,
                a.tone_reason,
                a.trust_score,
                a.bias_score,
                a.factual_rating,
                COALESCE(a.fact_check_status, 'unknown') AS fact_check_status,
                COALESCE(f.positive_count, 0) AS feedback_positive,
                COALESCE(f.negative_count, 0) AS feedback_negative
            FROM articles a
            LEFT JOIN article_feedback f ON f.article_id = a.id
            WHERE a.score > 0
              AND (a.published_at IS NULL
                   OR datetime(a.published_at) >= datetime('now', '-48 hours'))
              {where_region}
              {where_paywall}
              {where_sources}
              {where_tone}
            ORDER BY a.score DESC, datetime(a.published_at) DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    finally:
        conn.close()


def get_swipe_history(limit: int = 100) -> list[sqlite3.Row]:
    conn = _conn()
    try:
        return conn.execute(
            """
            SELECT
                sh.id AS swipe_id,
                sh.is_relevant,
                sh.swiped_at,
                a.id,
                a.title,
                a.source,
                a.published_at,
                a.url,
                a.topics,
                a.summary_json
            FROM swipe_history sh
            JOIN articles a ON a.id = sh.article_id
            ORDER BY sh.swiped_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()


def _normalize_key(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    raw = unicodedata.normalize("NFD", raw)
    return "".join(ch for ch in raw if unicodedata.category(ch) != "Mn")


def _canonical_category(value: str | None) -> str:
    key = _normalize_key(value)
    aliases = {
        "rikokset": "rikos",
        "rikos": "rikos",
        "saa": "saa",
        "ymparisto": "ymparisto",
        "kansainvaliset": "kansainvaliset",
    }
    return aliases.get(key, key)


def _categories_from_row(row: sqlite3.Row) -> set[str]:
    values: list[str] = []
    values.extend([row["category"], row["category_secondary"]])
    topics = json.loads(row["topics"] or "[]")
    if isinstance(topics, list):
        values.extend(topics)
    out: set[str] = set()
    for value in values:
        key = _canonical_category(value)
        if key:
            out.add(key)
    return out


def _build_region_where(
    scope_filters: list[str] | None = None,
    local_cities: list[str] | None = None,
) -> tuple[str, list[str]]:
    scopes = {_normalize_key(x) for x in (scope_filters or []) if _normalize_key(x)}
    cities = [_normalize_key(x) for x in (local_cities or []) if _normalize_key(x)]

    if not scopes and not cities:
        return "", []

    clauses: list[str] = []
    params: list[str] = []

    if "suomi" in scopes:
        clauses.append("a.region = 'suomi'")
    if "maailma" in scopes:
        clauses.append("a.region = 'maailma'")

    if "paikalliset" in scopes:
        if cities:
            placeholders = ",".join("?" * len(cities))
            clauses.append(f"a.region IN ({placeholders})")
            params.extend([f"paikalliset:{city}" for city in cities])
        else:
            clauses.append("a.region LIKE 'paikalliset:%'")
    elif cities:
        placeholders = ",".join("?" * len(cities))
        clauses.append(f"a.region IN ({placeholders})")
        params.extend([f"paikalliset:{city}" for city in cities])

    if not clauses:
        return "AND 1=0", []
    return f"AND ({' OR '.join(clauses)})", params


def list_articles(
    limit: int = 300,
    offset: int = 0,
    region_filters: list[str] | None = None,
    hide_paywall: bool = False,
    excluded_sources: list[str] | None = None,
    scope_filters: list[str] | None = None,
    local_cities: list[str] | None = None,
    source_filters: list[str] | None = None,
    category_filters: list[str] | None = None,
    tone_filters: list[str] | None = None,
) -> list[sqlite3.Row]:
    """Return latest articles for development browsing (not only swiped items)."""
    conn = _conn()
    try:
        params: list = []

        where_region = ""
        if scope_filters is not None or local_cities is not None:
            where_region, region_params = _build_region_where(scope_filters, local_cities)
            params.extend(region_params)
        elif region_filters:
            placeholders = ",".join("?" * len(region_filters))
            where_region = f"AND a.region IN ({placeholders})"
            params.extend(region_filters)

        where_paywall = "AND a.is_paywall = 0" if hide_paywall else ""

        where_sources = ""
        if source_filters:
            sp = ",".join("?" * len(source_filters))
            where_sources = f"AND a.source IN ({sp})"
            params.extend(source_filters)
        elif excluded_sources:
            sp = ",".join("?" * len(excluded_sources))
            where_sources = f"AND a.source NOT IN ({sp})"
            params.extend(excluded_sources)

        where_tone = ""
        normalized_tones = {_normalize_key(x) for x in (tone_filters or []) if _normalize_key(x)}
        if normalized_tones and "all" not in normalized_tones:
            expanded_tones: set[str] = set()
            for tone in normalized_tones:
                if tone == "neutral_positive":
                    expanded_tones.update(["neutral", "positive"])
                elif tone in {"positive", "neutral", "negative"}:
                    expanded_tones.add(tone)
            if expanded_tones:
                placeholders = ",".join("?" * len(expanded_tones))
                where_tone = f"AND a.tone IN ({placeholders})"
                params.extend(sorted(expanded_tones))
            else:
                where_tone = "AND 1=0"

        normalized_categories = {
            _canonical_category(x) for x in (category_filters or []) if _canonical_category(x)
        }

        if normalized_categories:
            # Category filtering must be done in Python — fetch all matching rows first
            rows = conn.execute(
                f"""
                SELECT
                    a.id,
                    a.title,
                    a.source,
                    a.region,
                    a.published_at,
                    a.url,
                    a.topics,
                    a.summary_json,
                    a.is_paywall,
                    a.score,
                    a.category,
                    a.category_secondary,
                    a.tone,
                    a.trust_score,
                    a.bias_score,
                    a.factual_rating,
                    COALESCE(a.fact_check_status, 'unknown') AS fact_check_status
                FROM articles a
                WHERE 1=1
                  {where_region}
                  {where_paywall}
                  {where_sources}
                  {where_tone}
                ORDER BY datetime(a.published_at) DESC, a.id DESC
                """,
                params,
            ).fetchall()
            rows = [
                row
                for row in rows
                if _categories_from_row(row).intersection(normalized_categories)
            ]
            return rows[offset: offset + limit]
        else:
            # No Python-side filtering needed — push LIMIT/OFFSET into SQL
            params_page = params + [limit, offset]
            rows = conn.execute(
                f"""
                SELECT
                    a.id,
                    a.title,
                    a.source,
                    a.region,
                    a.published_at,
                    a.url,
                    a.topics,
                    a.summary_json,
                    a.is_paywall,
                    a.score,
                    a.category,
                    a.category_secondary,
                    a.tone,
                    a.trust_score,
                    a.bias_score,
                    a.factual_rating,
                    COALESCE(a.fact_check_status, 'unknown') AS fact_check_status
                FROM articles a
                WHERE 1=1
                  {where_region}
                  {where_paywall}
                  {where_sources}
                  {where_tone}
                ORDER BY datetime(a.published_at) DESC, a.id DESC
                LIMIT ? OFFSET ?
                """,
                params_page,
            ).fetchall()
            return rows
    finally:
        conn.close()


def count_articles(
    region_filters: list[str] | None = None,
    hide_paywall: bool = False,
    excluded_sources: list[str] | None = None,
    scope_filters: list[str] | None = None,
    local_cities: list[str] | None = None,
    source_filters: list[str] | None = None,
    category_filters: list[str] | None = None,
    tone_filters: list[str] | None = None,
) -> dict[str, int]:
    """Return aggregate counts for the articles stat panel."""
    normalized_categories = {
        _canonical_category(x) for x in (category_filters or []) if _canonical_category(x)
    }

    # When category filters are active we still need Python-side filtering, so load all rows
    if normalized_categories:
        rows = list_articles(
            limit=10_000_000,
            offset=0,
            region_filters=region_filters,
            hide_paywall=hide_paywall,
            excluded_sources=excluded_sources,
            scope_filters=scope_filters,
            local_cities=local_cities,
            source_filters=source_filters,
            category_filters=category_filters,
            tone_filters=tone_filters,
        )
        total = len(rows)
        suomi = sum(1 for r in rows if r["region"] == "suomi")
        maailma = sum(1 for r in rows if r["region"] == "maailma")
        paywall = sum(1 for r in rows if bool(r["is_paywall"]))
        return {"total": total, "suomi": suomi, "maailma": maailma, "paywall": paywall}

    # Fast path: use SQL COUNT(*) — no need to load all rows into Python
    conn = _conn()
    try:
        params: list = []

        where_region = ""
        if scope_filters is not None or local_cities is not None:
            where_region, region_params = _build_region_where(scope_filters, local_cities)
            params.extend(region_params)
        elif region_filters:
            placeholders = ",".join("?" * len(region_filters))
            where_region = f"AND a.region IN ({placeholders})"
            params.extend(region_filters)

        where_paywall = "AND a.is_paywall = 0" if hide_paywall else ""

        where_sources = ""
        if source_filters:
            sp = ",".join("?" * len(source_filters))
            where_sources = f"AND a.source IN ({sp})"
            params.extend(source_filters)
        elif excluded_sources:
            sp = ",".join("?" * len(excluded_sources))
            where_sources = f"AND a.source NOT IN ({sp})"
            params.extend(excluded_sources)

        where_tone = ""
        normalized_tones = {_normalize_key(x) for x in (tone_filters or []) if _normalize_key(x)}
        if normalized_tones and "all" not in normalized_tones:
            expanded_tones: set[str] = set()
            for tone in normalized_tones:
                if tone == "neutral_positive":
                    expanded_tones.update(["neutral", "positive"])
                elif tone in {"positive", "neutral", "negative"}:
                    expanded_tones.add(tone)
            if expanded_tones:
                placeholders = ",".join("?" * len(expanded_tones))
                where_tone = f"AND a.tone IN ({placeholders})"
                params.extend(sorted(expanded_tones))
            else:
                where_tone = "AND 1=0"

        row = conn.execute(
            f"""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN a.region = 'suomi' THEN 1 ELSE 0 END) AS suomi,
                SUM(CASE WHEN a.region = 'maailma' THEN 1 ELSE 0 END) AS maailma,
                SUM(CASE WHEN a.is_paywall = 1 THEN 1 ELSE 0 END) AS paywall
            FROM articles a
            WHERE 1=1
              {where_region}
              {where_paywall}
              {where_sources}
              {where_tone}
            """,
            params,
        ).fetchone()
        return {
            "total": int(row["total"] or 0),
            "suomi": int(row["suomi"] or 0),
            "maailma": int(row["maailma"] or 0),
            "paywall": int(row["paywall"] or 0),
        }
    finally:
        conn.close()


def get_article_facets(
    hide_paywall: bool = False,
    excluded_sources: list[str] | None = None,
    scope_filters: list[str] | None = None,
    local_cities: list[str] | None = None,
) -> dict[str, Any]:
    rows = list_articles(
        limit=10_000_000,
        offset=0,
        hide_paywall=hide_paywall,
        excluded_sources=excluded_sources,
        scope_filters=scope_filters,
        local_cities=local_cities,
    )

    categories: dict[str, int] = {}
    sources: dict[str, int] = {}
    tones: dict[str, int] = {"positive": 0, "neutral": 0, "negative": 0}
    scopes = {"suomi": 0, "maailma": 0, "paikalliset": 0}
    cities: dict[str, int] = {}

    for row in rows:
        source = row["source"] or "Tuntematon"
        sources[source] = sources.get(source, 0) + 1

        tone = _normalize_key(row["tone"])
        if tone in tones:
            tones[tone] += 1

        region = row["region"] or ""
        if region == "suomi":
            scopes["suomi"] += 1
        elif region == "maailma":
            scopes["maailma"] += 1
        elif region.startswith("paikalliset:"):
            scopes["paikalliset"] += 1
            city = region.split(":", 1)[1]
            cities[city] = cities.get(city, 0) + 1

        for key in _categories_from_row(row):
            categories[key] = categories.get(key, 0) + 1

    return {
        "total": len(rows),
        "categories": categories,
        "sources": sources,
        "tones": tones,
        "scopes": scopes,
        "cities": cities,
    }


def top_feedback_metrics(limit: int = 10) -> dict[str, float | int | None]:
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT
                COALESCE(f.positive_count, 0) AS positive_count,
                COALESCE(f.negative_count, 0) AS negative_count
            FROM articles a
            LEFT JOIN article_feedback f ON f.article_id = a.id
            ORDER BY a.score DESC, datetime(a.published_at) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        total_positive = sum(int(row["positive_count"]) for row in rows)
        total_negative = sum(int(row["negative_count"]) for row in rows)
        total_votes = total_positive + total_negative
        ratio = round(total_positive / total_votes, 3) if total_votes else None
        return {
            "top_limit": limit,
            "total_feedback_votes": total_votes,
            "positive_feedback_ratio": ratio,
        }
    finally:
        conn.close()
