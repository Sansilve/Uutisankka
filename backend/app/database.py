import json
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

from .config import DB_PATH

_db_lock = Lock()


def _conn() -> sqlite3.Connection:
    db_path = Path(DB_PATH)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
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
            _ensure_column(conn, "user_preferences", "news_scope", "TEXT NOT NULL DEFAULT '[\"suomi\",\"maailma\"]'")
            _ensure_column(conn, "user_preferences", "local_city", "TEXT NOT NULL DEFAULT ''")
            _ensure_column(conn, "user_preferences", "hide_paywall", "INTEGER NOT NULL DEFAULT 1")
            _ensure_column(conn, "user_preferences", "excluded_sources", "TEXT NOT NULL DEFAULT '[]'")
            conn.commit()
        finally:
            conn.close()


def ensure_default_preferences() -> None:
    default_interests = ["technology", "politics", "economy"]
    default_dislikes = ["celebrity", "entertainment"]
    upsert_preferences(default_interests, default_dislikes, only_if_missing=True)


def upsert_preferences(
    interests: list[str],
    disliked_topics: list[str],
    news_scope: list[str] | None = None,
    local_city: str = "",
    hide_paywall: bool = True,
    excluded_sources: list[str] | None = None,
    only_if_missing: bool = False,
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
            timestamp = datetime.utcnow().isoformat()
            if existing:
                conn.execute(
                    """
                    UPDATE user_preferences
                    SET interests = ?, disliked_topics = ?, news_scope = ?, local_city = ?, hide_paywall = ?, excluded_sources = ?, updated_at = ?
                    WHERE user_id = 1
                    """,
                    (json.dumps(interests), json.dumps(disliked_topics), json.dumps(scope), local_city, int(hide_paywall), json.dumps(sources), timestamp),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO user_preferences (user_id, interests, disliked_topics, news_scope, local_city, hide_paywall, excluded_sources, updated_at)
                    VALUES (1, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (json.dumps(interests), json.dumps(disliked_topics), json.dumps(scope), local_city, int(hide_paywall), json.dumps(sources), timestamp),
                )
            conn.commit()
        finally:
            conn.close()


def get_preferences() -> dict:
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT interests, disliked_topics, news_scope, local_city, hide_paywall, excluded_sources FROM user_preferences WHERE user_id = 1"
        ).fetchone()
        if not row:
            return {
                "interests": ["politiikka", "teknologia", "talous"],
                "disliked_topics": ["viihde", "celebrity"],
                "news_scope": ["suomi", "maailma"],
                "local_city": "",
                "hide_paywall": True,
                "excluded_sources": [],
            }
        return {
            "interests": json.loads(row["interests"]),
            "disliked_topics": json.loads(row["disliked_topics"]),
            "news_scope": json.loads(row["news_scope"] or '["suomi","maailma"]'),
            "local_city": row["local_city"] or "",
            "hide_paywall": bool(row["hide_paywall"]),
            "excluded_sources": json.loads(row["excluded_sources"] or '[]'),
        }
    finally:
        conn.close()


def random_briefing(limit: int = 10, region_filters: list[str] | None = None, disliked_topics: list[str] | None = None, hide_paywall: bool = False, excluded_sources: list[str] | None = None) -> list:
    """Return *limit* random enriched articles (score > 0), shuffled each call."""
    conn = _conn()
    try:
        params: list = []
        where_region = ""
        if region_filters:
            placeholders = ",".join("?" * len(region_filters))
            where_region = f"AND a.region IN ({placeholders})"
            params.extend(region_filters)

        where_dislikes = ""
        if disliked_topics:
            dp = ",".join("?" * len(disliked_topics))
            where_dislikes = f"""
              AND NOT EXISTS (
                  SELECT 1 FROM json_each(a.topics)
                  WHERE json_each.value IN ({dp})
              )"""
            params.extend(disliked_topics)

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
                COALESCE(f.positive_count, 0) AS feedback_positive,
                COALESCE(f.negative_count, 0) AS feedback_negative
            FROM articles a
            LEFT JOIN article_feedback f ON f.article_id = a.id
            WHERE a.score > 0
              {where_region}
              {where_dislikes}
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
            SELECT id, title, source, published_at, content, url
            FROM articles
            WHERE summary_json = '{"bullets": []}'
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return rows
    finally:
        conn.close()


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
            SELECT id, title, source, published_at, content
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
            SELECT id, title, content, source, published_at, feedback_score
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
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT a.topics, s.is_relevant
            FROM swipe_history s
            JOIN articles a ON a.id = s.article_id
            WHERE a.topics IS NOT NULL AND a.topics != '[]'
            """
        ).fetchall()
    finally:
        conn.close()

    stats: dict[str, dict[str, int]] = {}
    for row in rows:
        topics: list[str] = json.loads(row["topics"] or "[]")
        is_positive = bool(row["is_relevant"])
        for topic in topics:
            if topic not in stats:
                stats[topic] = {"positive": 0, "total": 0}
            stats[topic]["total"] += 1
            if is_positive:
                stats[topic]["positive"] += 1
    return stats


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
) -> None:
    is_paywall_from_summary = 1 if summary.get("source") == "no_content" else 0
    with _db_lock:
        conn = _conn()
        try:
            existing = conn.execute("SELECT is_paywall FROM articles WHERE id = ?", (article_id,)).fetchone()
            existing_paywall = int(existing["is_paywall"]) if existing else 0
            is_paywall = 1 if (existing_paywall or is_paywall_from_summary) else 0
            if translated_title:
                conn.execute(
                    """
                    UPDATE articles
                    SET title = ?, base_score = ?, score = ?, topics = ?,
                        summary_json = ?, score_breakdown_json = ?, is_paywall = ?,
                        category = ?, category_secondary = ?,
                        tone = ?, tone_confidence = ?, tone_reason = ?
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
                        tone = ?, tone_confidence = ?, tone_reason = ?
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


def apply_feedback(article_id: int, is_relevant: bool) -> dict[str, float | int]:
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
                INSERT INTO swipe_history (article_id, is_relevant, swiped_at)
                VALUES (?, ?, ?)
                """,
                (article_id, 1 if is_relevant else 0, timestamp),
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


def top_briefing(limit: int = 10, region_filters: list[str] | None = None, disliked_topics: list[str] | None = None, hide_paywall: bool = False, excluded_sources: list[str] | None = None) -> list[sqlite3.Row]:
    conn = _conn()
    try:
        params: list = []
        where_region = ""
        if region_filters:
            placeholders = ",".join("?" * len(region_filters))
            where_region = f"AND a.region IN ({placeholders})"
            params.extend(region_filters)

        where_dislikes = ""
        if disliked_topics:
            dp = ",".join("?" * len(disliked_topics))
            where_dislikes = f"""
              AND NOT EXISTS (
                  SELECT 1 FROM json_each(a.topics)
                  WHERE json_each.value IN ({dp})
              )"""
            params.extend(disliked_topics)

        where_paywall = "AND a.is_paywall = 0" if hide_paywall else ""

        where_sources = ""
        if excluded_sources:
            sp = ",".join("?" * len(excluded_sources))
            where_sources = f"AND a.source NOT IN ({sp})"
            params.extend(excluded_sources)

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
                COALESCE(f.positive_count, 0) AS feedback_positive,
                COALESCE(f.negative_count, 0) AS feedback_negative
            FROM articles a
            LEFT JOIN article_feedback f ON f.article_id = a.id
            WHERE a.score > 0
              AND (a.published_at IS NULL
                   OR datetime(a.published_at) >= datetime('now', '-48 hours'))
              {where_region}
              {where_dislikes}
              {where_paywall}
              {where_sources}
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


def list_articles(
    limit: int = 300,
    region_filters: list[str] | None = None,
    hide_paywall: bool = False,
    excluded_sources: list[str] | None = None,
) -> list[sqlite3.Row]:
    """Return latest articles for development browsing (not only swiped items)."""
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

        return conn.execute(
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
                a.is_paywall
            FROM articles a
            WHERE 1=1
              {where_region}
              {where_paywall}
              {where_sources}
            ORDER BY datetime(a.published_at) DESC, a.id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    finally:
        conn.close()


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
