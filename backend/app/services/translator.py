"""
Article translator.

Detects articles from known English-language sources and translates them
to Finnish using a single LLM call that also produces bullet summaries.
This avoids two separate API calls (translate + summarize) per article.
"""

import logging
import re

from ..config import FALLBACK_LLM_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY, TRANSLATION_TARGET_LANG, TRANSLATION_TARGET_LANG_NAME
from .llm import LLMUnavailable, chat_with_fallback, validate_llm_response

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domains that publish in English — matched against article URL
# ---------------------------------------------------------------------------

ENGLISH_DOMAINS: frozenset[str] = frozenset(
    [
        "bbc.co.uk",
        "bbc.com",
        "bbci.co.uk",
        "nytimes.com",
        "theguardian.com",
        "washingtonpost.com",
        "aljazeera.com",
        "aljazeera.net",
        "reuters.com",
        "reutersagency.com",
        "apnews.com",
        "bloomberg.com",
        "ft.com",
        "economist.com",
        "politico.com",
        "foreignpolicy.com",
        "cnn.com",
        "skynews.com",
        "sky.com",
        "dw.com",
        "euronews.com",
        "npr.org",
        "france24.com",
        "rfi.fr",
        "finlandtoday.fi",
    ]
)


def is_english_url(url: str) -> bool:
    """Return True if the article URL belongs to a known English-language source."""
    url_lower = url.lower()
    return any(domain in url_lower for domain in ENGLISH_DOMAINS)


_LLM_AVAILABLE = bool(OPENAI_API_KEY or FALLBACK_LLM_API_KEY or GEMINI_API_KEY)


# ---------------------------------------------------------------------------
# Combined translate + summarize (one LLM call)
# ---------------------------------------------------------------------------

def _build_system_prompt(target_lang_name: str = TRANSLATION_TARGET_LANG_NAME) -> str:
    return (
        f"You are a professional news journalist writing in {target_lang_name}. "
        f"You will receive an English-language news article.\n"
        f"Do two things in one response:\n\n"
        f"1. Translate the headline to {target_lang_name} — short, concise, max 100 characters.\n"
        f"2. Summarize the article into 3–5 clear bullet points in {target_lang_name}.\n\n"
        f"Respond EXACTLY in this format (add nothing else):\n"
        f"HEADLINE: [translated headline in {target_lang_name}]\n"
        f"- [bullet 1]\n"
        f"- [bullet 2]\n"
        f"- [bullet 3]"
    )


_SYSTEM_PROMPT = _build_system_prompt()


def _is_title_echo(candidate: str, original_title: str) -> bool:
    """Return True when LLM headline is effectively unchanged from source title."""
    return candidate.strip().casefold() == original_title.strip().casefold()


def translate_and_summarize(
    title: str, content: str
) -> tuple[str, dict[str, list[str] | str]]:
    """Translate an English article title to Finnish and produce Finnish bullet summaries.

    Returns:
        (finnish_title, summary_dict)  where summary_dict = {"bullets": [...], "source": "llm"}
        On failure, returns the original title and an empty summary dict.
    """
    if not _LLM_AVAILABLE:
        return title, {"bullets": [], "source": "heuristic"}

    stripped = content.strip()
    sentence_count = len([s for s in re.split(r"[.!?]+", stripped) if len(s.strip()) > 20])
    if len(stripped) < 120 or sentence_count <= 1:
        from .summarizer import _deterministic_summarize
        return title, _deterministic_summarize(title, content)

    user_text = f"Otsikko (englanti): {title}\n\nArtikkeli (englanti): {content[:2500]}"
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]

    try:
        raw = chat_with_fallback(
            messages,
            max_tokens=450,
            temperature=0.3,
            validator=lambda text: validate_llm_response(
                text,
                min_bullets=3,
                input_text=user_text,
            ),
        )
        lines = [line.strip() for line in raw.splitlines() if line.strip()]

        finnish_title = title  # fallback
        title_echo_detected = False
        bullets: list[str] = []

        for line in lines:
            if line.upper().startswith("HEADLINE:"):
                extracted = line[len("HEADLINE:"):].strip()
                if extracted:
                    if _is_title_echo(extracted, title):
                        title_echo_detected = True
                    else:
                        finnish_title = extracted
            elif line.startswith(("-", "•", "*", "–")):
                bullet = line.lstrip("-•*– ").strip()
                if len(bullet) > 10:
                    bullets.append(bullet)

        if len(bullets) >= 3 and not title_echo_detected:
            return finnish_title, {"bullets": bullets[:5], "source": "llm"}

        # Premium retry: weak output gets one OpenAI-prioritised retry.
        if OPENAI_API_KEY:
            retry_raw = chat_with_fallback(
                messages,
                max_tokens=500,
                temperature=0.25,
                premium=True,
                validator=lambda text: validate_llm_response(
                    text,
                    min_bullets=3,
                    input_text=user_text,
                ),
            )
            retry_lines = [line.strip() for line in retry_raw.splitlines() if line.strip()]
            retry_title = finnish_title
            retry_title_echo_detected = title_echo_detected
            retry_bullets: list[str] = []
            for line in retry_lines:
                if line.upper().startswith("HEADLINE:"):
                    extracted = line[len("HEADLINE:"):].strip()
                    if extracted:
                        if _is_title_echo(extracted, title):
                            retry_title_echo_detected = True
                        else:
                            retry_title = extracted
                elif line.startswith(("-", "•", "*", "–")):
                    bullet = line.lstrip("-•*– ").strip()
                    if len(bullet) > 10:
                        retry_bullets.append(bullet)
            if retry_bullets and not retry_title_echo_detected:
                return retry_title, {"bullets": retry_bullets[:5], "source": "llm"}

        # LLM responded but we couldn't parse bullets — fall back to deterministic
        log.debug("translate_and_summarize: no bullets parsed from LLM response, using heuristic")
    except LLMUnavailable as exc:
        log.warning("translate_and_summarize: all LLM providers failed – %s", exc)

    # Deterministic fallback produces generic bullets rather than returning empty.
    from .summarizer import _deterministic_summarize
    return title, _deterministic_summarize(title, content)


_TITLE_ONLY_PROMPT = (
    f"Translate the following English news headline to {TRANSLATION_TARGET_LANG_NAME}. "
    f"Respond ONLY with the translated headline, max 120 characters, no explanations."
)


def translate_title(title: str) -> str | None:
    """Translate a single English title to Finnish. Returns None on failure."""
    if not _LLM_AVAILABLE:
        return None
    try:
        result = chat_with_fallback(
            messages=[
                {"role": "system", "content": _TITLE_ONLY_PROMPT},
                {"role": "user", "content": title},
            ],
            max_tokens=80,
            temperature=0.2,
            validator=lambda text: validate_llm_response(
                text,
                min_bullets=0,
                input_text=title,
            ),
        )
        # Reject if LLM echoed back English or returned garbage
        if result and result != title and len(result) >= 5:
            return result
    except LLMUnavailable:
        pass
    return None
