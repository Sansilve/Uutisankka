"""Unit tests for translator.py — T2+T3 parser and prompt robustness."""

import app.services.translator as translator


_TITLE = "Breaking storm hits city"
_CONTENT = (
    "The first sentence contains enough detail for parsing stability across providers. "
    "The second sentence adds context so sentence count threshold is satisfied. "
    "The third sentence ensures content is long enough to avoid deterministic early return."
)


def _patch_llm(monkeypatch, responses: list[str]) -> None:
    monkeypatch.setattr(translator, "_LLM_AVAILABLE", True)
    queue = list(responses)
    last = queue[-1] if queue else ""

    def _fake_chat(*args, **kwargs):
        if queue:
            return queue.pop(0)
        return last

    monkeypatch.setattr(translator, "chat_with_fallback", _fake_chat)


def _patch_deterministic(monkeypatch):
    import app.services.summarizer as summarizer
    monkeypatch.setattr(
        summarizer,
        "_deterministic_summarize",
        lambda *args, **kwargs: {"bullets": ["fallback bullet"], "source": "heuristic"},
    )


def test_prompt_contains_target_language_name():
    prompt = translator._build_system_prompt("Finnish")
    assert "Finnish" in prompt


def test_prompt_contains_custom_language():
    prompt = translator._build_system_prompt("Swedish")
    assert "Swedish" in prompt
    assert "Finnish" not in prompt


def test_prompt_contains_headline_format_marker():
    """Parser depends on HEADLINE: prefix — must be present in prompt."""
    prompt = translator._build_system_prompt("Finnish")
    assert "HEADLINE:" in prompt


def test_malformed_output_without_headline_prefix_keeps_original_title(monkeypatch):
    _patch_llm(
        monkeypatch,
        [
            "Intro text without expected marker\n"
            "- Ensimmainen bullet jossa tarpeeksi pituutta\n"
            "- Toinen bullet jossa tarpeeksi pituutta\n"
            "- Kolmas bullet jossa tarpeeksi pituutta"
        ],
    )
    title, summary = translator.translate_and_summarize(_TITLE, _CONTENT)
    assert title == _TITLE
    assert summary["source"] == "llm"
    assert len(summary["bullets"]) == 3


def test_empty_bullets_falls_back_to_heuristic(monkeypatch):
    _patch_llm(monkeypatch, ["HEADLINE: Uutisotsikko suomeksi"])
    title, summary = translator.translate_and_summarize(_TITLE, _CONTENT)
    assert title == _TITLE
    assert summary["source"] == "heuristic"
    # New fallback: minimal Finnish bullets using the English title, no raw English sentences
    assert any("Mitä tapahtui" in b for b in summary["bullets"])
    assert any("Tiivistelmä ei saatavilla" in b for b in summary["bullets"])


def test_title_echo_is_rejected_and_falls_back(monkeypatch):
    _patch_deterministic(monkeypatch)
    _patch_llm(
        monkeypatch,
        [
            "HEADLINE: Breaking storm hits city\n"
            "- Ensimmainen pitkä bullet joka muuten kelpaisi\n"
            "- Toinen pitkä bullet joka muuten kelpaisi\n"
            "- Kolmas pitkä bullet joka muuten kelpaisi"
        ],
    )
    title, summary = translator.translate_and_summarize(_TITLE, _CONTENT)
    assert title == _TITLE
    assert summary["source"] == "heuristic"


def test_very_long_response_does_not_crash_and_limits_bullets(monkeypatch):
    long_bullets = "\n".join([f"- Tämä on erittäin pitkä bullet numero {i} jossa on paljon tekstiä" for i in range(1, 20)])
    _patch_llm(monkeypatch, [f"HEADLINE: Pitka otsikko suomeksi\n{long_bullets}"])
    title, summary = translator.translate_and_summarize(_TITLE, _CONTENT)
    assert title == "Pitka otsikko suomeksi"
    assert summary["source"] == "llm"
    assert len(summary["bullets"]) == 5


def test_extra_whitespace_and_blank_lines_are_tolerated(monkeypatch):
    _patch_llm(
        monkeypatch,
        [
            "\n\nHEADLINE:   Suomennettu otsikko   \n\n"
            "  -   Ensimmainen bullet jossa on pituutta   \n\n"
            "  -   Toinen bullet jossa on pituutta   \n"
            "  -   Kolmas bullet jossa on pituutta   \n"
        ],
    )
    title, summary = translator.translate_and_summarize(_TITLE, _CONTENT)
    assert title == "Suomennettu otsikko"
    assert summary["source"] == "llm"
    assert len(summary["bullets"]) == 3


def test_bullet_marker_variations_are_all_recognized(monkeypatch):
    _patch_llm(
        monkeypatch,
        [
            "HEADLINE: Suomennettu otsikko\n"
            "- Ensimmainen bullet jossa on pituutta\n"
            "• Toinen bullet jossa on pituutta\n"
            "* Kolmas bullet jossa on pituutta\n"
            "– Neljas bullet jossa on pituutta"
        ],
    )
    title, summary = translator.translate_and_summarize(_TITLE, _CONTENT)
    assert title == "Suomennettu otsikko"
    assert summary["source"] == "llm"
    assert len(summary["bullets"]) == 4


def test_translation_target_lang_prompt_integration():
    prompt = translator._build_system_prompt("Finnish")
    assert "Translate the headline to Finnish" in prompt
    assert "bullet points in Finnish" in prompt
