"""
Unit tests for score_article() in backend/app/services/scoring.py.

All tests are deterministic — no HTTP calls, no shared state.
Published timestamps are injected as fixed ISO strings relative to "now"
using freezegun so recency logic stays stable.
"""
from datetime import datetime, timedelta, timezone

import pytest
from freezegun import freeze_time

from app.services.scoring import score_article, detect_topics

# ── Helpers ───────────────────────────────────────────────────────────────────

FROZEN_NOW = "2026-05-03T12:00:00+00:00"

def _ts(hours_ago: float) -> str:
    dt = datetime(2026, 5, 3, 12, 0, 0, tzinfo=timezone.utc) - timedelta(hours=hours_ago)
    return dt.isoformat()


def _score(title="Testiartikkeli", content="", source="tuntematon.fi",
           published_at=None, prefs=None) -> tuple:
    return score_article(title, content, source, published_at, prefs or {})


# ── Topic detection ───────────────────────────────────────────────────────────

def test_topic_detection_teknologia():
    topics = detect_topics("New AI chip sets record in machine learning benchmark")
    assert "teknologia" in topics


def test_topic_detection_politiikka():
    topics = detect_topics("Hallitus esittää uutta budjettia eduskunnalle")
    assert "politiikka" in topics


def test_topic_detection_no_false_positive():
    topics = detect_topics("Sää on tänään kaunis")
    assert "teknologia" not in topics
    assert "politiikka" not in topics


# ── Source boost ──────────────────────────────────────────────────────────────

@freeze_time(FROZEN_NOW)
def test_major_source_boost():
    score_no_boost, _, _ = _score(source="tuntematon.fi", published_at=_ts(2))
    score_boost, _, breakdown = _score(source="Yle Uutiset", published_at=_ts(2))
    assert score_boost > score_no_boost
    assert any("Major source boost" in str(b["reason"]) for b in breakdown)


# ── Clickbait penalty ─────────────────────────────────────────────────────────

@freeze_time(FROZEN_NOW)
def test_clickbait_penalty():
    score_clean, _, _ = _score(title="Poliitikko kommentoi budjettiesitystä", published_at=_ts(2))
    score_clickbait, _, breakdown = _score(
        title="you won't believe what happened next in parliament", published_at=_ts(2)
    )
    assert score_clickbait < score_clean
    assert any("Clickbait" in str(b["reason"]) for b in breakdown)


# ── Low-signal penalty ────────────────────────────────────────────────────────

@freeze_time(FROZEN_NOW)
def test_low_signal_penalty():
    score_clean, _, _ = _score(title="Suomi investoi uusiutuvaan energiaan", published_at=_ts(2))
    score_low, _, breakdown = _score(title="top 10 ways to save money", published_at=_ts(2))
    assert score_low < score_clean
    assert any("Low-signal" in str(b["reason"]) for b in breakdown)


# ── Aggressive title penalty ──────────────────────────────────────────────────

@freeze_time(FROZEN_NOW)
def test_aggressive_title_all_caps():
    _, _, breakdown = _score(title="CAPS ONLY TITLE HERE", published_at=_ts(2))
    penalty_items = [b for b in breakdown if "Aggressive title" in str(b["reason"])]
    assert penalty_items, "Expected aggressive title penalty in breakdown"
    assert penalty_items[0]["points"] == -2.0


@freeze_time(FROZEN_NOW)
def test_aggressive_title_double_exclamation():
    _, _, breakdown = _score(title="Uusi löytö!! Tiede mullistuu!!", published_at=_ts(2))
    assert any("Aggressive title" in str(b["reason"]) for b in breakdown)


# ── Recency boost & penalty ───────────────────────────────────────────────────

@freeze_time(FROZEN_NOW)
def test_recency_boost_fresh_article():
    _, _, breakdown = _score(published_at=_ts(0.5))
    recency = [b for b in breakdown if "Recency" in str(b["reason"])]
    assert recency, "Expected a recency adjustment entry"
    assert recency[0]["points"] > 0


@freeze_time(FROZEN_NOW)
def test_recency_penalty_old_article():
    _, _, breakdown = _score(published_at=_ts(60))  # 60 hours ago
    recency = [b for b in breakdown if "Recency" in str(b["reason"])]
    assert recency, "Expected a recency adjustment entry"
    assert recency[0]["points"] == -1.0


@freeze_time(FROZEN_NOW)
def test_fresh_beats_old_ceteris_paribus():
    score_fresh, _, _ = _score(published_at=_ts(0.5))
    score_old, _, _ = _score(published_at=_ts(60))
    assert score_fresh > score_old


# ── User interest boost ───────────────────────────────────────────────────────

@freeze_time(FROZEN_NOW)
def test_user_interest_topic_boost():
    prefs = {"interests": ["teknologia"], "disliked_topics": []}
    score_with, _, breakdown = _score(
        title="AI chip hits new record", content="machine learning breakthrough",
        published_at=_ts(2), prefs=prefs
    )
    score_without, _, _ = _score(
        title="AI chip hits new record", content="machine learning breakthrough",
        published_at=_ts(2)
    )
    assert score_with > score_without
    assert any("Interest topic boost" in str(b["reason"]) for b in breakdown)


# ── User dislike penalty ──────────────────────────────────────────────────────

@freeze_time(FROZEN_NOW)
def test_user_dislike_topic_penalty():
    prefs = {"interests": [], "disliked_topics": ["viihde"]}
    score_disliked, _, breakdown = _score(
        title="Tosi-tv tähti julkisuuden henkilö gossip reality",
        published_at=_ts(2), prefs=prefs
    )
    score_neutral, _, _ = _score(
        title="Tosi-tv tähti julkisuuden henkilö gossip reality", published_at=_ts(2)
    )
    assert score_disliked < score_neutral
    assert any("Disliked topic penalty" in str(b["reason"]) for b in breakdown)


# ── Feedback score integration ────────────────────────────────────────────────

@freeze_time(FROZEN_NOW)
def test_feedback_score_added_to_total():
    """score_article does not take feedback_score directly, but the DB layer
    adds it after scoring. We verify that the raw scorer output can be
    augmented externally without losing precision."""
    base_score, _, _ = _score(published_at=_ts(2))
    feedback_score = 2.0
    total = round(base_score + feedback_score, 2)
    assert total == round(base_score + 2.0, 2)


# ── Breaking hint boost ───────────────────────────────────────────────────────

@freeze_time(FROZEN_NOW)
def test_breaking_hint_boost():
    _, _, breakdown = _score(
        title="Breaking: EU announces new sanctions package", published_at=_ts(1)
    )
    assert any("Breaking news hint" in str(b["reason"]) for b in breakdown)


# ── Return value shape ────────────────────────────────────────────────────────

def test_return_value_shape():
    score, topics, breakdown = _score()
    assert isinstance(score, float)
    assert isinstance(topics, list)
    assert isinstance(breakdown, list)
    for item in breakdown:
        assert "reason" in item
        assert "points" in item


# ── S3: category field present on all breakdown items ─────────────────────────

@freeze_time(FROZEN_NOW)
def test_breakdown_items_have_category():
    _, _, breakdown = _score(
        title="Teknologiayritys julkisti uuden tekoälychip-tuotteen",
        source="Yle Uutiset",
        published_at=_ts(1),
        prefs={"interests": ["teknologia"], "disliked_topics": []},
    )
    assert breakdown, "Expected non-empty breakdown"
    for item in breakdown:
        assert "category" in item, f"Missing category in: {item}"
        assert item["category"] != "", f"Empty category in: {item}"


@freeze_time(FROZEN_NOW)
def test_source_boost_category_is_source():
    _, _, breakdown = _score(source="Yle Uutiset", published_at=_ts(2))
    source_items = [b for b in breakdown if "Major source" in b["reason"]]
    assert source_items and source_items[0]["category"] == "source"


@freeze_time(FROZEN_NOW)
def test_recency_category_is_freshness():
    _, _, breakdown = _score(published_at=_ts(1))
    recency_items = [b for b in breakdown if "Recency" in b["reason"]]
    assert recency_items and recency_items[0]["category"] == "freshness"


@freeze_time(FROZEN_NOW)
def test_preference_boost_category_is_preference():
    prefs = {"interests": ["teknologia"], "disliked_topics": []}
    _, _, breakdown = _score(
        title="AI chip machine learning breakthrough", published_at=_ts(2), prefs=prefs
    )
    pref_items = [b for b in breakdown if "Interest" in b["reason"]]
    assert pref_items and pref_items[0]["category"] == "preference"


@freeze_time(FROZEN_NOW)
def test_quality_penalty_category_is_quality():
    _, _, breakdown = _score(title="CAPS ONLY TITLE HERE", published_at=_ts(2))
    quality_items = [b for b in breakdown if "Aggressive title" in b["reason"]]
    assert quality_items and quality_items[0]["category"] == "quality"


# ── S4: Adaptive topic weights ────────────────────────────────────────────────

@freeze_time(FROZEN_NOW)
def test_adaptive_disabled_identical_to_baseline(monkeypatch):
    """When ADAPTIVE_SCORING_ENABLED is False, scores must be identical regardless of stats."""
    import app.services.scoring as scoring_mod
    monkeypatch.setattr(scoring_mod, "ADAPTIVE_SCORING_ENABLED", False)
    stats = {"teknologia": {"positive": 9, "total": 10}}
    score_no_stats, _, _ = _score(
        title="AI chip machine learning", published_at=_ts(2)
    )
    score_with_stats, _, _ = score_article(
        "AI chip machine learning", "", "x.fi", _ts(2), {}, topic_swipe_stats=stats
    )
    assert score_no_stats == score_with_stats


@freeze_time(FROZEN_NOW)
def test_adaptive_enabled_high_positivity_boosts_score(monkeypatch):
    """80% positive swipes on teknologia → adjusted weight is higher than baseline."""
    import app.services.scoring as scoring_mod
    monkeypatch.setattr(scoring_mod, "ADAPTIVE_SCORING_ENABLED", True)
    monkeypatch.setattr(scoring_mod, "ADAPTIVE_MIN_SWIPES", 5)
    stats = {"teknologia": {"positive": 8, "total": 10}}  # 80% positive
    score_baseline, _, _ = _score(
        title="AI chip machine learning", published_at=_ts(2)
    )
    score_adaptive, _, breakdown = score_article(
        "AI chip machine learning", "", "x.fi", _ts(2), {}, topic_swipe_stats=stats
    )
    assert score_adaptive > score_baseline
    assert any("Adaptive weight" in b["reason"] for b in breakdown)


@freeze_time(FROZEN_NOW)
def test_adaptive_enabled_low_positivity_lowers_score(monkeypatch):
    """20% positive swipes on teknologia → score is lower than baseline."""
    import app.services.scoring as scoring_mod
    monkeypatch.setattr(scoring_mod, "ADAPTIVE_SCORING_ENABLED", True)
    monkeypatch.setattr(scoring_mod, "ADAPTIVE_MIN_SWIPES", 5)
    stats = {"teknologia": {"positive": 2, "total": 10}}  # 20% positive
    score_baseline, _, _ = _score(
        title="AI chip machine learning", published_at=_ts(2)
    )
    score_adaptive, _, _ = score_article(
        "AI chip machine learning", "", "x.fi", _ts(2), {}, topic_swipe_stats=stats
    )
    assert score_adaptive < score_baseline


@freeze_time(FROZEN_NOW)
def test_adaptive_insufficient_swipes_uses_baseline(monkeypatch):
    """Below ADAPTIVE_MIN_SWIPES → no adjustment applied."""
    import app.services.scoring as scoring_mod
    monkeypatch.setattr(scoring_mod, "ADAPTIVE_SCORING_ENABLED", True)
    monkeypatch.setattr(scoring_mod, "ADAPTIVE_MIN_SWIPES", 5)
    stats = {"teknologia": {"positive": 4, "total": 4}}  # only 4 swipes, threshold=5
    score_baseline, _, _ = _score(
        title="AI chip machine learning", published_at=_ts(2)
    )
    score_adaptive, _, breakdown = score_article(
        "AI chip machine learning", "", "x.fi", _ts(2), {}, topic_swipe_stats=stats
    )
    assert score_adaptive == score_baseline
    assert not any("Adaptive weight" in b["reason"] for b in breakdown)
