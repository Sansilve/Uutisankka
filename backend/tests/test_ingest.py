from app.services import ingest


def _make_row(article_id: int, title: str = "Test", url: str = "https://example.com/a"):
    return {
        "id": article_id,
        "title": title,
        "url": url,
        "content": "content text",
        "source": "Example Source",
        "published_at": None,
    }


def test_below_threshold_uses_deterministic_without_llm(monkeypatch):
    row = _make_row(1, title="English headline", url="https://bbc.com/news/1")
    calls = {"translate": 0, "summarize": 0, "deterministic": 0, "updated": []}

    monkeypatch.setattr(ingest, "TRANSLATION_SCORE_THRESHOLD", 0.5)
    monkeypatch.setattr(ingest, "get_preferences", lambda: {"interests": [], "disliked_topics": []})
    monkeypatch.setattr(ingest, "fetch_unenriched", lambda limit=300: [row])
    monkeypatch.setattr(ingest, "get_article_feedback_score", lambda article_id: 0.0)
    monkeypatch.setattr(ingest, "get_topic_swipe_stats", lambda: {})
    monkeypatch.setattr(ingest, "rescore_all", lambda preferences=None: 0)

    def fake_score_article(title, content, source, published_at, preferences, **kwargs):
        return -0.2, ["kansainväliset"], [{"reason": "pre", "points": -0.2}]

    monkeypatch.setattr(ingest, "score_article", fake_score_article)

    def fake_translate(*args, **kwargs):
        calls["translate"] += 1
        return "Suomennettu", {"bullets": ["x"], "source": "llm"}

    def fake_summarize(*args, **kwargs):
        calls["summarize"] += 1
        return {"bullets": ["x"], "source": "llm"}

    def fake_deterministic(*args, **kwargs):
        calls["deterministic"] += 1
        return {"bullets": ["fallback"], "source": "heuristic"}

    def fake_update(article_id, base_score, total_score, topics, summary, breakdown, translated_title=None):
        calls["updated"].append(
            {
                "article_id": article_id,
                "base_score": base_score,
                "summary_source": summary.get("source"),
                "translated_title": translated_title,
            }
        )

    monkeypatch.setattr(ingest, "translate_and_summarize", fake_translate)
    monkeypatch.setattr(ingest, "summarize_article", fake_summarize)
    monkeypatch.setattr(ingest, "_deterministic_summarize", fake_deterministic)
    monkeypatch.setattr(ingest, "update_article_enrichment", fake_update)

    result = ingest.enrich_unprocessed_articles()

    assert result == 1
    assert calls["translate"] == 0
    assert calls["summarize"] == 0
    assert calls["deterministic"] == 1
    assert calls["updated"][0]["summary_source"] == "heuristic"
    assert calls["updated"][0]["translated_title"] is None


def test_above_threshold_english_routes_to_translation_llm(monkeypatch):
    row = _make_row(2, title="English headline", url="https://bbc.com/news/2")
    calls = {"translate": 0, "summarize": 0, "deterministic": 0, "updated": []}

    monkeypatch.setattr(ingest, "TRANSLATION_SCORE_THRESHOLD", 0.0)
    monkeypatch.setattr(ingest, "get_preferences", lambda: {"interests": [], "disliked_topics": []})
    monkeypatch.setattr(ingest, "fetch_unenriched", lambda limit=300: [row])
    monkeypatch.setattr(ingest, "get_article_feedback_score", lambda article_id: 0.0)
    monkeypatch.setattr(ingest, "get_topic_swipe_stats", lambda: {})
    monkeypatch.setattr(ingest, "rescore_all", lambda preferences=None: 0)

    score_calls = {"n": 0}

    def fake_score_article(title, content, source, published_at, preferences, **kwargs):
        score_calls["n"] += 1
        # First pre-score qualifies for LLM route, second score uses translated title.
        if score_calls["n"] == 1:
            return 1.0, ["kansainväliset"], [{"reason": "pre", "points": 1.0}]
        return 1.2, ["kansainväliset"], [{"reason": "post", "points": 1.2}]

    monkeypatch.setattr(ingest, "score_article", fake_score_article)

    def fake_translate(*args, **kwargs):
        calls["translate"] += 1
        return "Suomennettu otsikko", {"bullets": ["llm"], "source": "llm"}

    def fake_summarize(*args, **kwargs):
        calls["summarize"] += 1
        return {"bullets": ["x"], "source": "llm"}

    def fake_deterministic(*args, **kwargs):
        calls["deterministic"] += 1
        return {"bullets": ["fallback"], "source": "heuristic"}

    def fake_update(article_id, base_score, total_score, topics, summary, breakdown, translated_title=None):
        calls["updated"].append(
            {
                "article_id": article_id,
                "base_score": base_score,
                "summary_source": summary.get("source"),
                "translated_title": translated_title,
            }
        )

    monkeypatch.setattr(ingest, "translate_and_summarize", fake_translate)
    monkeypatch.setattr(ingest, "summarize_article", fake_summarize)
    monkeypatch.setattr(ingest, "_deterministic_summarize", fake_deterministic)
    monkeypatch.setattr(ingest, "update_article_enrichment", fake_update)

    result = ingest.enrich_unprocessed_articles()

    assert result == 1
    assert calls["translate"] == 1
    assert calls["summarize"] == 0
    assert calls["deterministic"] == 0


# ── F2: Source quality tier tests ─────────────────────────────────────────────

def _make_row_source(article_id, source, content="x" * 50, url="https://example.com/a"):
    return {"id": article_id, "title": "Headline", "url": url,
            "content": content, "source": source, "published_at": None}


def _patch_common(monkeypatch, row, calls):
    monkeypatch.setattr(ingest, "TRANSLATION_SCORE_THRESHOLD", 0.0)
    monkeypatch.setattr(ingest, "get_preferences", lambda: {"interests": [], "disliked_topics": []})
    monkeypatch.setattr(ingest, "fetch_unenriched", lambda limit=300: [row])
    monkeypatch.setattr(ingest, "get_article_feedback_score", lambda article_id: 0.0)
    monkeypatch.setattr(ingest, "rescore_all", lambda preferences=None: 0)
    monkeypatch.setattr(ingest, "score_article",
                        lambda **kw: (1.0, [], [{"reason": "r", "points": 1.0, "category": "source"}]))
    monkeypatch.setattr(ingest, "translate_and_summarize",
                        lambda *a, **kw: (calls.__setitem__("llm", True) or ("FI", {"bullets": [], "source": "llm"})))
    monkeypatch.setattr(ingest, "summarize_article",
                        lambda *a, **kw: (calls.__setitem__("llm", True) or {"bullets": [], "source": "llm"}))
    monkeypatch.setattr(ingest, "_deterministic_summarize",
                        lambda *a, **kw: {"bullets": [], "source": "heuristic"})
    monkeypatch.setattr(ingest, "update_article_enrichment", lambda *a, **kw: None)


def test_low_tier_short_content_skips_llm(monkeypatch):
    """Low-tier source with content below LOW_TIER_MIN_CONTENT_LENGTH → no LLM call."""
    calls = {"llm": False}
    # content shorter than LOW_TIER_MIN_CONTENT_LENGTH (300) but longer than MIN_CONTENT_LENGTH (150)
    short_content = "x" * 200
    row = _make_row_source(10, source="prnewswire.com", content=short_content)
    _patch_common(monkeypatch, row, calls)
    monkeypatch.setattr(ingest, "LOW_TIER_MIN_CONTENT_LENGTH", 300)
    monkeypatch.setattr(ingest, "MIN_CONTENT_LENGTH", 150)

    ingest.enrich_unprocessed_articles()

    assert not calls["llm"], "LLM should NOT be called for low-tier short content"


def test_high_tier_short_content_allows_llm(monkeypatch):
    """High-tier source is not subject to low-tier threshold — normal path."""
    calls = {"llm": False}
    short_content = "x" * 200  # same length as above
    row = _make_row_source(11, source="yle.fi", content=short_content,
                           url="https://yle.fi/news/1")
    _patch_common(monkeypatch, row, calls)
    monkeypatch.setattr(ingest, "LOW_TIER_MIN_CONTENT_LENGTH", 300)
    monkeypatch.setattr(ingest, "MIN_CONTENT_LENGTH", 150)

    ingest.enrich_unprocessed_articles()

    assert calls["llm"], "LLM SHOULD be called for high-tier source regardless of low-tier threshold"
