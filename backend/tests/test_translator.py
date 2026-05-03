"""Unit tests for translator.py — T2: target language config."""

from app.services.translator import _build_system_prompt


def test_prompt_contains_target_language_name():
    prompt = _build_system_prompt("Finnish")
    assert "Finnish" in prompt


def test_prompt_contains_custom_language():
    prompt = _build_system_prompt("Swedish")
    assert "Swedish" in prompt
    assert "Finnish" not in prompt


def test_prompt_contains_headline_format_marker():
    """Parser depends on HEADLINE: prefix — must be present in prompt."""
    prompt = _build_system_prompt("Finnish")
    assert "HEADLINE:" in prompt
