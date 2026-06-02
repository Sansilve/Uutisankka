"""
Smoke tests for critical UutisAnkka API endpoints (Issue #15).

Covered:
  GET  /api/health
  GET  /api/briefing
  GET  /api/preferences
  PUT  /api/preferences
  POST /api/feedback
  GET  /api/history
"""


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------


def test_health_returns_200(client):
    r = client.get("/api/health")
    assert r.status_code == 200


def test_health_body(client):
    r = client.get("/api/health")
    assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /api/briefing
# ---------------------------------------------------------------------------


def test_briefing_returns_200(client):
    r = client.get("/api/briefing")
    assert r.status_code == 200


def test_briefing_schema(client):
    body = client.get("/api/briefing").json()
    assert "generated_at" in body
    assert "total" in body
    assert "stories" in body
    assert isinstance(body["stories"], list)


def test_briefing_total_matches_stories(client):
    body = client.get("/api/briefing").json()
    assert body["total"] == len(body["stories"])


# ---------------------------------------------------------------------------
# GET /api/preferences
# ---------------------------------------------------------------------------


def test_get_preferences_returns_200(client):
    r = client.get("/api/preferences")
    assert r.status_code == 200


def test_get_preferences_schema(client):
    body = client.get("/api/preferences").json()
    assert "interests" in body
    assert "disliked_topics" in body
    assert "news_scope" in body
    assert isinstance(body["interests"], list)
    assert isinstance(body["disliked_topics"], list)


# ---------------------------------------------------------------------------
# PUT /api/preferences
# ---------------------------------------------------------------------------


def test_put_preferences_returns_200(client):
    payload = {
        "interests": ["teknologia", "talous"],
        "disliked_topics": ["viihde"],
        "news_scope": ["suomi"],
        "local_city": "",
        "hide_paywall": False,
        "excluded_sources": [],
    }
    r = client.put("/api/preferences", json=payload)
    assert r.status_code == 200


def test_put_preferences_persisted(client):
    payload = {
        "interests": ["urheilu"],
        "disliked_topics": [],
        "news_scope": ["maailma"],
        "local_city": "Tampere",
        "hide_paywall": True,
        "excluded_sources": [],
    }
    client.put("/api/preferences", json=payload)
    body = client.get("/api/preferences").json()
    assert body["interests"] == ["urheilu"]
    assert body["local_city"] == "Tampere"
    assert body["hide_paywall"] is True


def test_put_preferences_missing_field_returns_422(client):
    # interests is required
    r = client.put("/api/preferences", json={"disliked_topics": []})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/feedback
# ---------------------------------------------------------------------------


def test_post_feedback_returns_200(client):
    r = client.post("/api/feedback", json={"article_id": 1, "is_relevant": True})
    assert r.status_code == 200


def test_post_feedback_schema(client):
    body = client.post("/api/feedback", json={"article_id": 2, "is_relevant": False}).json()
    assert "article_id" in body
    assert "feedback_positive" in body
    assert "feedback_negative" in body
    assert "feedback_score" in body
    assert "total_score" in body


def test_post_feedback_increments_positive(client):
    # Send two positive votes and verify count increases
    r1 = client.post("/api/feedback", json={"article_id": 42, "is_relevant": True}).json()
    r2 = client.post("/api/feedback", json={"article_id": 42, "is_relevant": True}).json()
    assert r2["feedback_positive"] == r1["feedback_positive"] + 1


def test_post_feedback_missing_field_returns_422(client):
    r = client.post("/api/feedback", json={"article_id": 1})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/history
# ---------------------------------------------------------------------------


def test_get_history_returns_200(client):
    r = client.get("/api/history")
    assert r.status_code == 200


def test_get_history_schema(client):
    body = client.get("/api/history").json()
    assert "total" in body
    assert "items" in body
    assert isinstance(body["items"], list)


def test_get_history_total_matches_items(client):
    body = client.get("/api/history").json()
    assert body["total"] == len(body["items"])


def test_get_history_contains_feedback_swipes(client):
    """History requires a JOIN with articles; insert a real article first."""
    import app.database as _db

    # Insert a minimal article directly so the JOIN in get_swipe_history works.
    with _db._db_lock:
        conn = _db._conn()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO articles
                    (id, title, source, url, content_hash, base_score,
                     feedback_score, score, topics, summary_json, created_at)
                VALUES (999, 'Test article', 'test', 'https://example.com/test',
                        'testhash999', 0, 0, 0, '[]', '{"bullets":[]}',
                        datetime('now'))
                """
            )
            conn.commit()
        finally:
            conn.close()

    client.post("/api/feedback", json={"article_id": 999, "is_relevant": True})
    body = client.get("/api/history").json()
    swiped_ids = {item["id"] for item in body["items"]}
    assert 999 in swiped_ids


# ---------------------------------------------------------------------------
# GET /api/metrics
# ---------------------------------------------------------------------------


def test_get_metrics_returns_200(client):
    r = client.get("/api/metrics")
    assert r.status_code == 200


def test_get_metrics_contains_scoring_version(client):
    body = client.get("/api/metrics").json()
    assert "scoring_version" in body
    assert body["scoring_version"] in {"v1", "v2"}


# ---------------------------------------------------------------------------
# GET /api/admin/llm-stats
# ---------------------------------------------------------------------------


def test_get_admin_llm_stats_returns_200(client):
    r = client.get("/api/admin/llm-stats")
    assert r.status_code == 200


def test_get_admin_llm_stats_schema(client):
    body = client.get("/api/admin/llm-stats").json()
    assert isinstance(body, dict)
    for provider_name, stats in body.items():
        assert isinstance(provider_name, str)
        assert isinstance(stats, dict)
        assert "calls" in stats
        assert "successes" in stats
        assert "failures" in stats
        assert "rate_limit_count" in stats
        assert "validation_rejections" in stats
        assert "p50_ms" in stats
        assert "p95_ms" in stats


# ---------------------------------------------------------------------------
# GET /api/admin/ingest-stats
# ---------------------------------------------------------------------------


def test_get_admin_ingest_stats_returns_200(client):
    r = client.get("/api/admin/ingest-stats")
    assert r.status_code == 200


def test_get_admin_ingest_stats_schema(client):
    body = client.get("/api/admin/ingest-stats").json()
    assert isinstance(body, dict)
    assert "translated_llm" in body
    assert "translated_heuristic" in body
    assert "filtered_below_threshold" in body
    assert "cache_hits" in body
    assert "paywall_detected" in body
    assert "scrape_attempted" in body
    assert "scrape_succeeded" in body
    assert "alerts" in body
    assert isinstance(body["alerts"], list)

    for key, value in body.items():
        if key == "alerts":
            continue
        assert isinstance(key, str)
        assert isinstance(value, int)
