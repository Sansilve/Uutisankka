"""
Article summarizer.

Primary path  : OpenAI chat completion → 3–5 Finnish bullet points.
Fallback path : Deterministic heuristic summarizer (no API key required).
"""

import re
from collections import Counter

from ..config import FALLBACK_LLM_API_KEY, GEMINI_API_KEY, OLLAMA_ENABLED, OPENAI_API_KEY
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

- Osapuolet: VAIN merkittävät henkilöt tai organisaatiot. Käytä AINA nominatiivia \
(perusmuoto, ei taivutettuna — ei 'Tokion' vaan 'Tokio', ei 'Instagramissa' vaan 'Instagram'). \
Kirjoita henkilöiden KOKO NIMI yhtenä kohtana (etunimi + sukunimi), esim. "Alisa Vainio", \
"Petteri Orpo". Muut esimerkit: "Euroopan komissio", "Instagram". \
ÄLÄ listaa saman henkilön etu- ja sukunimeä erillisinä — ne kuuluvat yhteen. \
JÄÄ POIS jos osapuolet ovat tuntemattomia tai yleisiä (poliitikko, asiantuntija).

- Tausta: Relevantti konteksti — vain jos selittää miksi tilanne on syntynyt.

TÄRKEÄÄ:
- Jos artikkelin sisältö on niukka, kirjoita vain "Mitä tapahtui"
- Älä koskaan kirjoita kahta bulletia jotka sanovat saman asian eri sanoin
- Älä listaa osapuolia jos ne eivät tuo ymmärrystä — jätä kohta pois mieluummin
- Kirjoita vain bullet-pisteet, ei johdantoa eikä loppusanoja
\
"""


def _dedup_bullets(bullets: list[str]) -> list[str]:
    """Remove bullets whose content portion is near-identical to a preceding bullet."""
    seen_content: list[str] = []
    result: list[str] = []
    for bullet in bullets:
        # Strip known Finnish label prefixes to compare content only
        content_part = re.sub(
            r"^(Mitä tapahtui|Miksi tärkeää|Osapuolet|Tausta):\s*",
            "",
            bullet,
            flags=re.IGNORECASE,
        ).strip().lower()
        # Reject if content starts with same 60 chars as an already-seen bullet
        prefix = content_part[:60]
        if not any(prefix and seen.startswith(prefix) for seen in seen_content):
            result.append(bullet)
            seen_content.append(content_part)
    return result


def _llm_summarize(title: str, content: str) -> dict[str, list[str]] | None:
    if not (OPENAI_API_KEY or FALLBACK_LLM_API_KEY or GEMINI_API_KEY or OLLAMA_ENABLED):
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
        bullets = _dedup_bullets(bullets)
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


# Common Finnish locative/case suffixes to strip (longest first prevents partial matches)
_FI_CASE_SUFFIXES = (
    "issa", "issä", "ista", "istä",   # inessive/elative of -inen words
    "ssa", "ssä", "sta", "stä",        # inessive, elative
    "lle", "lla", "llä", "lta", "ltä", # allative, adessive, ablative
    "ksi", "na", "nä",                 # translative, essive
)


def _strip_fi_suffix(word: str) -> str:
    """Approximate Finnish nominative by stripping one common case suffix."""
    low = word.lower()
    for suffix in _FI_CASE_SUFFIXES:
        if low.endswith(suffix) and len(word) > len(suffix) + 2:
            return word[: -len(suffix)]
    # Genitive -n: strip only when stem is 4+ chars and ends in a vowel
    if low.endswith("n") and len(word) >= 5 and low[-2] in "aeiouäö":
        return word[:-1]
    return word


def _extract_entities(text: str) -> list[str]:
    # Capture runs of consecutive Title-Cased words as multi-word proper nouns
    # Supports Finnish characters (Ä Ö Å)
    raw_phrases: list[str] = re.findall(
        r"\b[A-ZÄÖÅ][a-zA-ZäöåÄÖÅ\-]{1,}(?:\s+[A-ZÄÖÅ][a-zA-ZäöåÄÖÅ\-]{1,})*\b",
        text,
    )
    counts = Counter(raw_phrases)
    seen: set[str] = set()
    result: list[str] = []
    for phrase, _ in counts.most_common(8):
        words = phrase.split()
        # Strip case suffix from the last word only (typically carries inflection)
        words[-1] = _strip_fi_suffix(words[-1])
        norm = " ".join(words)
        key = norm.lower()
        if key not in seen:
            seen.add(key)
            result.append(norm)
        if len(result) >= 4:
            break
    return result


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

    _IMPACT_TOKENS = [
        # Finnish
        "koska", "siksi", "tämän vuoksi", "sen seurauksena", "vaikutus", "vaikuttaa",
        "riski", "merkittävä", "tärkeä", "seuraus", "johtaa", "uhkaa", "hyöty",
        "talous", "politiikka", "turvallisuus", "terveys",
        # English (for English-language content)
        "because", "impact", "risk", "market", "policy", "economy", "security",
        "significant", "critical", "affect", "threat", "benefit",
    ]
    # Only accept impact_sentence that is genuinely distinct from lead
    impact_sentence = next(
        (
            s
            for s in sentences
            if s.strip() != lead.strip()
            and any(token in s.lower() for token in _IMPACT_TOKENS)
        ),
        None,
    )
    # If no keyword match, use the second sentence — but only if it's different
    if impact_sentence is None and len(sentences) > 1:
        candidate = sentences[1]
        if candidate.strip() != lead.strip():
            impact_sentence = candidate

    entities = _extract_entities(f"{title}. {' '.join(sentences[:4])}")
    entities_line = ", ".join(entities) if entities else "Ei tunnistettu"

    bullets = [f"Mitä tapahtui: {lead}"]
    if impact_sentence:  # Only add Miksi tärkeää when genuinely different from lead
        bullets.append(f"Miksi tärkeää: {impact_sentence}")
    bullets.append(f"Osapuolet: {entities_line}.")

    seen = {lead, impact_sentence or ""}
    extra = [s for s in sentences[1:5] if s not in seen]
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
    
    Validates LLM output: rejects summaries with <2 bullets (triggers fallback).
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
    
    # Validation gate: LLM output must have at least 2 bullets
    if result is not None:
        bullets = result.get("bullets", [])
        if len(bullets) < 2:
            log.debug("summarize: LLM output rejected (only %d bullets), using fallback", len(bullets))
            result = None
    
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

