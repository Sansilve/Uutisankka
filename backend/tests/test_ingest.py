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
    monkeypatch.setattr(ingest, "rescore_all", lambda preferences=None: 0)

    def fake_score_article(title, content, source, published_at, preferences):
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
    monkeypatch.setattr(ingest, "rescore_all", lambda preferences=None: 0)

    score_calls = {"n": 0}

    def fake_score_article(title, content, source, published_at, preferences):
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
    assert calls["updated"][0]["summary_source"] == "llm"
    assert calls["updated"][0]["translated_title"] == "Suomennettu otsikko"
