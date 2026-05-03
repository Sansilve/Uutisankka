"""Unit tests for classifier.py — LLM article category classifier."""

import json
import pytest

from app.services.classifier import (
    ALLOWED_CATEGORIES,
    ClassificationResult,
    _parse_response,
    classify_article,
)


# ---------------------------------------------------------------------------
# _parse_response — JSON parsing
# ---------------------------------------------------------------------------

def _make_json(primary="technology", secondary=None, primary_conf=0.9, secondary_conf=0.0):
    data = {
        "primary": primary,
        "secondary": [secondary] if secondary else [],
        "confidence": {"primary": primary_conf, "secondary": secondary_conf},
    }
    return json.dumps(data)


def test_parse_valid_primary_only():
    result = _parse_response(_make_json("politics", primary_conf=0.9))
    assert result is not None
    assert result.primary == "politics"
    assert result.secondary is None


def test_parse_valid_with_secondary():
    raw = _make_json("science", secondary="health", primary_conf=0.85, secondary_conf=0.7)
    result = _parse_response(raw)
    assert result is not None
    assert result.primary == "science"
    assert result.secondary == "health"


def test_parse_secondary_dropped_below_threshold():
    """Secondary confidence below 0.5 → secondary dropped."""
    raw = _make_json("business", secondary="politics", primary_conf=0.8, secondary_conf=0.3)
    result = _parse_response(raw)
    assert result is not None
    assert result.primary == "business"
    assert result.secondary is None


def test_parse_primary_below_threshold_returns_none():
    """Primary confidence below 0.6 → whole result discarded."""
    raw = _make_json("weather", primary_conf=0.4)
    result = _parse_response(raw)
    assert result is None


def test_parse_invalid_category_returns_none():
    raw = _make_json("gossip", primary_conf=0.9)
    result = _parse_response(raw)
    assert result is None


def test_parse_secondary_same_as_primary_dropped():
    """Secondary that equals primary must not be kept."""
    raw = _make_json("sports", secondary="sports", primary_conf=0.9, secondary_conf=0.8)
    result = _parse_response(raw)
    assert result is not None
    assert result.secondary is None


def test_parse_wrapped_in_code_fence():
    """LLM sometimes wraps JSON in markdown code fences — must still parse."""
    inner = _make_json("culture", primary_conf=0.75)
    raw = f"```json\n{inner}\n```"
    result = _parse_response(raw)
    assert result is not None
    assert result.primary == "culture"


def test_parse_garbage_returns_none():
    assert _parse_response("This article is about sports.") is None
    assert _parse_response("") is None
    assert _parse_response("{broken json}") is None


# ---------------------------------------------------------------------------
# ALLOWED_CATEGORIES completeness
# ---------------------------------------------------------------------------

def test_allowed_categories_are_expected():
    expected = {"technology", "business", "politics", "sports", "weather", "culture", "science", "health"}
    assert ALLOWED_CATEGORIES == expected


# ---------------------------------------------------------------------------
# classify_article — integration with mock LLM
# ---------------------------------------------------------------------------

def test_classify_returns_none_when_llm_unavailable(monkeypatch):
    import app.services.classifier as cls_module
    monkeypatch.setattr(cls_module, "_LLM_AVAILABLE", False)
    result = classify_article("Some title", "Some content", "source.fi", "https://source.fi/article")
    assert result is None


def test_classify_uses_llm_response(monkeypatch):
    import app.services.classifier as cls_module

    fake_response = _make_json("technology", secondary="business", primary_conf=0.9, secondary_conf=0.6)
    monkeypatch.setattr(cls_module, "_LLM_AVAILABLE", True)
    monkeypatch.setattr(
        cls_module,
        "chat_with_fallback",
        lambda *a, **kw: fake_response,
    )

    result = classify_article("AI startup raises $100M", "Long content about AI investment...", "techcrunch.com", "https://techcrunch.com/ai-funding")
    assert result is not None
    assert result.primary == "technology"
    assert result.secondary == "business"


def test_classify_returns_none_on_llm_unavailable_exception(monkeypatch):
    import app.services.classifier as cls_module
    from app.services.llm import LLMUnavailable

    monkeypatch.setattr(cls_module, "_LLM_AVAILABLE", True)
    monkeypatch.setattr(
        cls_module,
        "chat_with_fallback",
        lambda *a, **kw: (_ for _ in ()).throw(LLMUnavailable("all failed")),
    )

    result = classify_article("Title", "Content", "source", "https://example.com")
    assert result is None


def test_classify_low_confidence_primary_returns_none(monkeypatch):
    import app.services.classifier as cls_module

    fake_response = _make_json("sports", primary_conf=0.3)
    monkeypatch.setattr(cls_module, "_LLM_AVAILABLE", True)
    monkeypatch.setattr(cls_module, "chat_with_fallback", lambda *a, **kw: fake_response)

    result = classify_article("Title", "Content", "source", "https://example.com")
    assert result is None


# ---------------------------------------------------------------------------
# System prompt structure
# ---------------------------------------------------------------------------

def test_system_prompt_contains_all_allowed_categories():
    from app.services.classifier import _SYSTEM_PROMPT
    for cat in ALLOWED_CATEGORIES:
        assert cat in _SYSTEM_PROMPT, f"Allowed category '{cat}' not found in system prompt"


def test_system_prompt_requests_json_output():
    from app.services.classifier import _SYSTEM_PROMPT
    assert "JSON" in _SYSTEM_PROMPT
    assert "primary" in _SYSTEM_PROMPT
    assert "secondary" in _SYSTEM_PROMPT
    assert "confidence" in _SYSTEM_PROMPT
