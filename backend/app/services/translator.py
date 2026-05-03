"""
Article translator.

Detects articles from known English-language sources and translates them
to Finnish using a single LLM call that also produces bullet summaries.
This avoids two separate API calls (translate + summarize) per article.
"""

import logging
import re

from ..config import FALLBACK_LLM_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY
from .llm import LLMUnavailable, chat_with_fallback

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

_SYSTEM_PROMPT = """\
Olet suomenkielinen uutistoimittaja. Saat englanninkielisen uutisen.
Tee kaksi asiaa yhdessä vastauksessa:

1. Käännä otsikko suomeksi — lyhyt, tiivis, max 100 merkkiä.
2. Tiivistä artikkeli 3–5 selkeäksi bullet-pisteeksi suomeksi.

Vastaa TÄSMÄLLEEN tässä muodossa (älä lisää mitään muuta):
OTSIKKO: [suomeksi käännetty otsikko]
- [bullet 1]
- [bullet 2]
- [bullet 3]\
"""


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
        raw = chat_with_fallback(messages, max_tokens=450, temperature=0.3)
        lines = [line.strip() for line in raw.splitlines() if line.strip()]

        finnish_title = title  # fallback
        bullets: list[str] = []

        for line in lines:
            if line.upper().startswith("OTSIKKO:"):
                extracted = line[len("OTSIKKO:"):].strip()
                if extracted:
                    finnish_title = extracted
            elif line.startswith(("-", "•", "*", "–")):
                bullet = line.lstrip("-•*– ").strip()
                if len(bullet) > 10:
                    bullets.append(bullet)

        if len(bullets) >= 3:
            return finnish_title, {"bullets": bullets[:5], "source": "llm"}

        # Premium retry: weak output gets one OpenAI-prioritised retry.
        if OPENAI_API_KEY:
            retry_raw = chat_with_fallback(messages, max_tokens=500, temperature=0.25, premium=True)
            retry_lines = [line.strip() for line in retry_raw.splitlines() if line.strip()]
            retry_title = finnish_title
            retry_bullets: list[str] = []
            for line in retry_lines:
                if line.upper().startswith("OTSIKKO:"):
                    extracted = line[len("OTSIKKO:"):].strip()
                    if extracted:
                        retry_title = extracted
                elif line.startswith(("-", "•", "*", "–")):
                    bullet = line.lstrip("-•*– ").strip()
                    if len(bullet) > 10:
                        retry_bullets.append(bullet)
            if retry_bullets:
                return retry_title, {"bullets": retry_bullets[:5], "source": "llm"}

        # LLM responded but we couldn't parse bullets — fall back to deterministic
        log.debug("translate_and_summarize: no bullets parsed from LLM response, using heuristic")
    except LLMUnavailable as exc:
        log.warning("translate_and_summarize: all LLM providers failed – %s", exc)

    # Deterministic fallback produces generic bullets rather than returning empty.
    from .summarizer import _deterministic_summarize
    return title, _deterministic_summarize(title, content)


_TITLE_ONLY_PROMPT = """\
Käännä seuraava englanninkielinen uutisotsikko suomeksi. \
Vastaa VAIN käännetyllä otsikolla, max 120 merkkiä, ei selityksiä.\
"""


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
        )
        # Reject if LLM echoed back English or returned garbage
        if result and result != title and len(result) >= 5:
            return result
    except LLMUnavailable:
        pass
    return None
