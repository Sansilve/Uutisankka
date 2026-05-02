"""
Article summarizer.

Primary path  : OpenAI chat completion → 3–5 Finnish bullet points.
Fallback path : Deterministic heuristic summarizer (no API key required).
"""

import re
from collections import Counter

from openai import OpenAI, OpenAIError

from ..config import LLM_MODEL, OPENAI_API_KEY

# ---------------------------------------------------------------------------
# Shared OpenAI client (lazy-initialised once)
# ---------------------------------------------------------------------------

_client: OpenAI | None = None


def _get_client() -> OpenAI | None:
    if not OPENAI_API_KEY:
        return None
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


# ---------------------------------------------------------------------------
# LLM summariser
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
Olet kokenut uutistoimittaja joka osaa selittää uutisten merkityksen lukijalle.

Tehtäväsi: tiivistä uutinen alla olevaan muotoon suomeksi.

RAKENNE (käytä aina tässä järjestyksessä, mutta vain jos sisältö on erilainen):

- Mitä tapahtui: Vastaa kysymykseen "mitä?" — konkreettinen fakta tai tapahtuma. \
Esimerkiksi: "Tampereen kaupunginvaltuusto hyväksyi budjettileikkaukset" tai \
"Uusi tutkimus osoittaa että vitamiini D vähentää COVID-riskiä". \
Ei saa olla otsikon toisto, vaan TARKEMPI tai ERILAINEN kuvaus.

- Miksi tärkeää: Vastaa kysymykseen "miksi tämä merkitsee?" — anna näkökulma tai seuraukset. \
Esimerkiksi: "Leikkaukset vaikuttavat palvelujen saatavuuteen" tai \
"Tutkimus voi muuttaa hoito-ohjeita miljoonille ihmisille". \
ÄLÄ toista "Mitä tapahtui" -kohtaa eri sanoin. Saa käyttää yleistietoa artikkelin lisäksi.

- Osapuolet: VAIN jos henkilöt/organisaatiot ovat merkittäviä tai yllättäviä. \
Esimerkiksi: "Pääministeri Orpo", "Euroopan komissio", "OpenAI". \
JÄÄ POIS jos osapuolet ovat tuntemattomia tai yleisiä (poliitikko, asiantuntija).

- Tausta: Relevantti konteksti — vain jos selittää miksi tilanne on syntynyt.

TÄRKEÄÄ:
- Jos artikkelin sisältö on niukka, kirjoita vain "Mitä tapahtui"
- Älä koskaan kirjoita kahta bulletia jotka sanovat saman asian eri sanoin
- Älä listaa osapuolia jos ne eivät tuo ymmärrystä — jätä kohta pois mieluummin
- Kirjoita vain bullet-pisteet, ei johdantoa eikä loppusanoja
\
"""


def _llm_summarize(title: str, content: str) -> dict[str, list[str]] | None:
    client = _get_client()
    if client is None:
        return None

    user_text = f"Otsikko: {title}\n\nSisältö: {content[:2500]}"

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            max_tokens=400,
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        bullets = [
            line.lstrip("•*-– ").strip()
            for line in raw.splitlines()
            if line.strip()
        ]
        bullets = [b for b in bullets if len(b) > 10]
        if bullets:
            return {"bullets": bullets[:5], "source": "llm"}
    except OpenAIError:
        pass

    return None


# ---------------------------------------------------------------------------
# Deterministic fallback (heuristic, English labels kept for compat)
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 25]


def _extract_entities(text: str) -> list[str]:
    matches = re.findall(r"\b[A-Z][a-zA-Z\-]{2,}\b", text)
    counts = Counter(matches)
    return [item for item, _ in counts.most_common(4)]


def _deterministic_summarize(title: str, content: str) -> dict[str, list[str]]:
    sentences = _split_sentences(content)

    if not sentences:
        return {
            "bullets": [
                f"Mitä tapahtui: {title}",
                "Miksi tärkeää: Mahdollisesti merkityksellinen tapahtuma, mutta syötetekstissä on vähän yksityiskohtia.",
                "Osapuolet: Ei riittävästi kontekstia tunnistamiseen.",
            ],
            "source": "heuristic",
        }

    lead = sentences[0]
    impact_sentence = next(
        (
            s
            for s in sentences
            if any(
                token in s.lower()
                for token in ["because", "impact", "risk", "market", "policy", "economy",
                              "koska", "vaikutus", "riski", "talous", "politiikka"]
            )
        ),
        sentences[min(1, len(sentences) - 1)],
    )

    entities = _extract_entities(f"{title}. {' '.join(sentences[:4])}")
    entities_line = ", ".join(entities) if entities else "Ei tunnistettu"

    bullets = [
        f"Mitä tapahtui: {lead}",
        f"Miksi tärkeää: {impact_sentence}",
        f"Osapuolet: {entities_line}.",
    ]

    extra = [s for s in sentences[1:5] if s not in {lead, impact_sentence}]
    for sentence in extra[:2]:
        bullets.append(f"Tausta: {sentence}")

    return {"bullets": bullets[:5], "source": "heuristic"}


# ---------------------------------------------------------------------------
# Public interface (unchanged signature — ingest.py calls this)
# ---------------------------------------------------------------------------

def summarize_article(title: str, content: str, source: str = "") -> dict[str, list[str]]:
    """Return a summary dict with key 'bullets' (list of strings).

    Tries the OpenAI LLM first; falls back to the deterministic heuristic
    summariser when the API key is absent or the API call fails.
    """
    # If content is essentially just the title repeated (paywall), skip LLM.
    # We check if the content (stripped) is nearly identical to the title —
    # not just "short", since a real article can have a short lead sentence.
    stripped = content.strip() if content else ""
    title_stripped = title.strip()
    # Normalize both for comparison: lowercase, collapse whitespace
    def _norm(s: str) -> str:
        return re.sub(r"\s+", " ", s.lower().strip())
    norm_content = _norm(stripped)
    norm_title = _norm(title_stripped)
    source_norm = _norm(source)

    # Paywall keywords in Finnish/English that indicate subscriber-only content
    _PAYWALL_WORDS = [
        "tilaajille", "tilaa", "vain tilaajille", "maksullinen",
        "subscribers only", "premium", "paywall",
    ]
    has_paywall_word = any(w in norm_content for w in _PAYWALL_WORDS)

    # Many international wire/public-broadcaster feeds are free by design.
    # For those, avoid aggressive "short teaser" rules to reduce false positives.
    _FREE_SOURCE_HINTS = [
        "guardian", "bbc", "reuters",
        "al jazeera", "france 24", "sky news", "rfi", "upi", "npr", "cnn", "dw",
        "euronews", "global news", "yle",
    ]
    _PAYWALLED_SOURCE_HINTS = [
        "helsingin sanomat", "aamulehti", "iltalehti", "ilta-sanomat",
        "satakunnan", "hameen sanomat", "ksml", "savonsanomat", "kaleva",
        "uusimaa", "esaimaa", "aamuposti", "maaseudun tulevaisuus",
        # International paywall sources
        "nyt", "new york times", "nytimes",
        "washington post", "financial times",
        "la times", "latimes", "los angeles times",
    ]
    _MIXED_TABLOID_HINTS = [
        "iltalehti", "ilta-sanomat",
    ]
    is_likely_free_source = any(h in source_norm for h in _FREE_SOURCE_HINTS)
    is_likely_paywalled_source = any(h in source_norm for h in _PAYWALLED_SOURCE_HINTS)
    is_mixed_tabloid_source = any(h in source_norm for h in _MIXED_TABLOID_HINTS)

    # Count sentences: real articles have multiple sentences
    sentence_count = len([s for s in re.split(r'[.!?]+', stripped) if len(s.strip()) > 15])

    structural_paywall = (
        len(stripped) < 30  # essentially empty
        or norm_content == norm_title  # content is exactly the title
        or (len(stripped) < 80 and norm_title.startswith(norm_content[:40]))  # content is prefix of title
        or (len(stripped) < 80 and norm_content.startswith(norm_title[:40]))  # content starts with title
    )

    teaser_paywall = (
        len(stripped) < 150
        or (len(stripped) < 350 and sentence_count <= 2)
        or (len(stripped) < 500 and sentence_count <= 1)
    )

    # Global safety rule:
    # - Mark paywall directly only from hard evidence (keyword/structural match).
    # - Allow teaser-based paywall only for clearly paywalled sources.
    hard_paywall = structural_paywall or has_paywall_word
    if hard_paywall:
        is_paywall = True
    elif is_likely_paywalled_source and not is_mixed_tabloid_source:
        is_paywall = teaser_paywall
    elif is_mixed_tabloid_source:
        # IS/IL feeds often have very short but free leads.
        is_paywall = len(stripped) < 120 and sentence_count <= 1
    else:
        # For free/unknown sources, do not mark paywall from short teaser alone.
        is_paywall = False

    if is_paywall:
        return {"bullets": [], "source": "no_content"}

    result = _llm_summarize(title, content)
    if result is not None:
        return result
    return _deterministic_summarize(title, content)

