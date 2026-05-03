import app.services.scoring as scoring
from app.models import PreferenceProfile


def test_preference_profile_defaults_have_no_entertainment_dislikes():
    prefs = PreferenceProfile()
    lowered = {x.lower() for x in prefs.disliked_topics}
    assert "celebrity" not in lowered
    assert "viihde" not in lowered


def test_onboarding_interest_affects_first_scoring_breakdown(monkeypatch):
    monkeypatch.setattr(scoring, "SCORING_VERSION", "v2", raising=False)
    monkeypatch.setattr(scoring, "ADAPTIVE_SCORING_ENABLED", True, raising=False)

    score, topics, breakdown = scoring.score_article(
        title="Uusi tekoälyratkaisu suomalaiseen teollisuuteen",
        content="Teknologia ja tekoäly muuttavat tuotantoa nopeasti.",
        source="Yle Uutiset",
        published_at=None,
        preferences={
            "interests": ["teknologia"],
            "disliked_topics": [],
        },
        topic_swipe_stats=None,
        source_swipe_stats=None,
        category_swipe_stats=None,
    )

    assert score != 0
    assert "teknologia" in topics
    reasons = [item["reason"] for item in breakdown]
    assert any(str(reason).startswith("Topic affinity: teknologia") for reason in reasons)
