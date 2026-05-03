import pytest

from app.services import llm


class MockProvider:
    def __init__(self, name, result="", available=True, error=None, calls=None):
        self.name = name
        self.result = result
        self.available = available
        self.error = error
        self.calls = calls if calls is not None else []

    def is_available(self):
        return self.available

    def chat(self, messages, max_tokens, temperature):
        self.calls.append(self.name)
        if self.error is not None:
            raise self.error
        return self.result


def test_default_mode_uses_low_cost_rotation_first(monkeypatch):
    calls = []
    fallback = MockProvider("fallback", result="fallback answer", calls=calls)
    gemini = MockProvider("gemini", result="gemini answer", calls=calls)
    openai = MockProvider("openai", result="openai answer", calls=calls)

    monkeypatch.setattr(
        llm,
        "_provider_registry",
        {
            "openai": openai,
            "fallback": fallback,
            "gemini": gemini,
        },
    )
    monkeypatch.setattr(llm, "_rotation_cursor", 0)

    result = llm.chat_with_fallback(messages=[{"role": "user", "content": "hi"}])

    assert result == "fallback answer"
    assert calls == ["fallback"]


def test_rotation_advances_between_calls(monkeypatch):
    calls = []
    fallback = MockProvider("fallback", result="fallback answer", calls=calls)
    gemini = MockProvider("gemini", result="gemini answer", calls=calls)
    openai = MockProvider("openai", available=False, calls=calls)

    monkeypatch.setattr(
        llm,
        "_provider_registry",
        {
            "openai": openai,
            "fallback": fallback,
            "gemini": gemini,
        },
    )
    monkeypatch.setattr(llm, "_rotation_cursor", 0)

    first = llm.chat_with_fallback(messages=[{"role": "user", "content": "a"}])
    second = llm.chat_with_fallback(messages=[{"role": "user", "content": "b"}])

    assert first == "fallback answer"
    assert second == "gemini answer"
    assert calls == ["fallback", "gemini"]


def test_premium_mode_prioritizes_openai(monkeypatch):
    calls = []
    fallback = MockProvider("fallback", result="fallback answer", calls=calls)
    gemini = MockProvider("gemini", result="gemini answer", calls=calls)
    openai = MockProvider("openai", result="openai answer", calls=calls)

    monkeypatch.setattr(
        llm,
        "_provider_registry",
        {
            "openai": openai,
            "fallback": fallback,
            "gemini": gemini,
        },
    )

    result = llm.chat_with_fallback(
        messages=[{"role": "user", "content": "hi"}],
        premium=True,
    )

    assert result == "openai answer"
    assert calls == ["openai"]


def test_provider_failure_falls_through_to_next(monkeypatch):
    calls = []
    fallback = MockProvider("fallback", error=RuntimeError("boom"), calls=calls)
    gemini = MockProvider("gemini", result="gemini answer", calls=calls)
    openai = MockProvider("openai", result="openai answer", calls=calls)

    monkeypatch.setattr(
        llm,
        "_provider_registry",
        {
            "openai": openai,
            "fallback": fallback,
            "gemini": gemini,
        },
    )
    monkeypatch.setattr(llm, "_rotation_cursor", 0)

    result = llm.chat_with_fallback(messages=[{"role": "user", "content": "hi"}])

    assert result == "gemini answer"
    assert calls == ["fallback", "gemini"]


def test_provider_timeout_falls_through_to_next(monkeypatch):
    calls = []
    fallback = MockProvider("fallback", error=TimeoutError("slow provider"), calls=calls)
    gemini = MockProvider("gemini", result="gemini answer", calls=calls)
    openai = MockProvider("openai", result="openai answer", calls=calls)

    monkeypatch.setattr(
        llm,
        "_provider_registry",
        {
            "openai": openai,
            "fallback": fallback,
            "gemini": gemini,
        },
    )
    monkeypatch.setattr(llm, "_rotation_cursor", 0)

    result = llm.chat_with_fallback(messages=[{"role": "user", "content": "hi"}])

    assert result == "gemini answer"
    assert calls == ["fallback", "gemini"]


def test_unavailable_providers_are_skipped(monkeypatch):
    calls = []
    fallback = MockProvider("fallback", available=False, calls=calls)
    gemini = MockProvider("gemini", available=False, calls=calls)
    openai = MockProvider("openai", result="openai answer", calls=calls)

    monkeypatch.setattr(
        llm,
        "_provider_registry",
        {
            "openai": openai,
            "fallback": fallback,
            "gemini": gemini,
        },
    )

    result = llm.chat_with_fallback(messages=[{"role": "user", "content": "hi"}])

    assert result == "openai answer"
    assert calls == ["openai"]


def test_validation_rejection_falls_through_to_next_provider(monkeypatch):
    calls = []
    fallback = MockProvider("fallback", result="OTSIKKO: sama", calls=calls)
    gemini = MockProvider("gemini", result="- valid bullet", calls=calls)
    openai = MockProvider("openai", result="openai answer", calls=calls)

    monkeypatch.setattr(
        llm,
        "_provider_registry",
        {
            "openai": openai,
            "fallback": fallback,
            "gemini": gemini,
        },
    )
    monkeypatch.setattr(llm, "_rotation_cursor", 0)

    result = llm.chat_with_fallback(
        messages=[{"role": "user", "content": "hi"}],
        validator=lambda text: llm.validate_llm_response(text, min_bullets=1),
    )

    assert result == "- valid bullet"
    assert calls == ["fallback", "gemini"]


def test_validate_llm_response_rejects_empty():
    ok, reason = llm.validate_llm_response("", min_bullets=1)
    assert ok is False
    assert reason == "empty_response"


def test_validate_llm_response_rejects_echo():
    ok, reason = llm.validate_llm_response(
        "   User: hello world   ",
        min_bullets=0,
        input_text="User: hello world",
    )
    assert ok is False
    assert reason == "echo_response"


def test_validate_llm_response_rejects_without_required_bullets():
    ok, reason = llm.validate_llm_response("OTSIKKO: Testi", min_bullets=1)
    assert ok is False
    assert reason.startswith("insufficient_bullets")


def test_validate_llm_response_accepts_valid_bullets():
    ok, reason = llm.validate_llm_response("- Ensimmainen\n- Toinen", min_bullets=1)
    assert ok is True
    assert reason == "ok"


def test_raises_when_nothing_configured(monkeypatch):
    monkeypatch.setattr(llm, "_provider_registry", {})

    with pytest.raises(llm.LLMUnavailable, match="No LLM provider configured"):
        llm.chat_with_fallback(messages=[{"role": "user", "content": "hi"}])
