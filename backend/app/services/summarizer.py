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
Olet kokenut uutistoimittaja. Lue alla oleva uutinen ja tiivistä se 3–5 \
selkeäksi bullet-pisteeksi suomeksi. Käytä seuraavia otsikoita tarpeen mukaan:

- Mitä tapahtui: [yksi selkeä lause]
- Miksi tärkeää: [vaikutus tai merkitys]
- Osapuolet: [henkilöt, organisaatiot tai maat]
- Tausta: [konteksti tai aiemmat tapahtumat]
- Lisätietoa: [muu olennainen tieto]

Kirjoita vain bullet-pisteet. Älä lisää johdantoa tai loppusanoja.\
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

def summarize_article(title: str, content: str) -> dict[str, list[str]]:
    """Return a summary dict with key 'bullets' (list of strings).

    Tries the OpenAI LLM first; falls back to the deterministic heuristic
    summariser when the API key is absent or the API call fails.
    """
    result = _llm_summarize(title, content)
    if result is not None:
        return result
    return _deterministic_summarize(title, content)

