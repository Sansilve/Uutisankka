"""
Article summarizer.

Primary path  : OpenAI chat completion → 3–5 Finnish bullet points.
Fallback path : Deterministic heuristic summarizer (no API key required).
"""

import re
from collections import Counter

from ..config import FALLBACK_LLM_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY
from .llm import LLMUnavailable, chat_with_fallback, validate_llm_response
from .paywall import assess_paywall


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
    if not (OPENAI_API_KEY or FALLBACK_LLM_API_KEY or GEMINI_API_KEY):
        return None

    user_text = f"Otsikko: {title}\n\nSisältö: {content[:2500]}"
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]

    try:
        raw = chat_with_fallback(
            messages=messages,
            max_tokens=400,
            temperature=0.3,
            validator=lambda text: validate_llm_response(
                text,
                min_bullets=1,
                input_text=user_text,
            ),
        )
        bullets = [
            line.lstrip("•*-– ").strip()
            for line in raw.splitlines()
            if line.strip()
        ]
        bullets = [b for b in bullets if len(b) > 10]
        if bullets:
            return {"bullets": bullets[:5], "source": "llm"}
    except LLMUnavailable:
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
    assessment = assess_paywall(title=title, content=content, source=source)

    if assessment.status == "paywalled":
        return {
            "bullets": [],
            "source": "no_content",
            "paywall_status": assessment.status,
            "paywall_score": assessment.score,
            "paywall_reasons": assessment.reasons,
            "paywall_signals": assessment.signals.__dict__,
        }

    result = _llm_summarize(title, content)
    if result is not None:
        result["paywall_status"] = assessment.status
        result["paywall_score"] = assessment.score
        result["paywall_reasons"] = assessment.reasons
        result["paywall_signals"] = assessment.signals.__dict__
        return result

    fallback = _deterministic_summarize(title, content)
    fallback["paywall_status"] = assessment.status
    fallback["paywall_score"] = assessment.score
    fallback["paywall_reasons"] = assessment.reasons
    fallback["paywall_signals"] = assessment.signals.__dict__
    return fallback

