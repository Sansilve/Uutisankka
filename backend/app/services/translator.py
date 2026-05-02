"""
Article translator.

Detects articles from known English-language sources and translates them
to Finnish using a single LLM call that also produces bullet summaries.
This avoids two separate API calls (translate + summarize) per article.
"""

import logging

from ..config import FALLBACK_LLM_API_KEY, OPENAI_API_KEY
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


_LLM_AVAILABLE = bool(OPENAI_API_KEY or FALLBACK_LLM_API_KEY)


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

        if bullets:
            return finnish_title, {"bullets": bullets[:5], "source": "llm"}

    except LLMUnavailable as exc:
        log.warning("translate_and_summarize: all LLM providers failed – %s", exc)

    return title, {"bullets": [], "source": "heuristic"}


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
