"""
Source trust and bias lookup service.

Primary data: backend/data/source_registry.json (MBFC-based curated registry)
Fallback for unknown sources: Ollama LLM prompt (optional, best-effort).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

_REGISTRY_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "source_registry.json"

# Factual rating → trust_score mapping (used for unknown sources resolved via LLM)
_RATING_TO_TRUST: dict[str, int] = {
    "VERY HIGH": 95,
    "HIGH": 85,
    "MOSTLY FACTUAL": 65,
    "MIXED": 45,
    "LOW": 25,
    "VERY LOW": 10,
    "FAKE NEWS": 0,
}

# Bias label → bias_score mapping
_LABEL_TO_BIAS: dict[str, int] = {
    "EXTREME-LEFT": -3,
    "LEFT": -2,
    "LEFT-CENTER": -1,
    "CENTER": 0,
    "RIGHT-CENTER": 1,
    "RIGHT": 2,
    "EXTREME-RIGHT": 3,
}

# Low-reliability factual ratings that trigger a scoring penalty in scoring.py
LOW_TRUST_RATINGS: frozenset[str] = frozenset({"LOW", "VERY LOW", "FAKE NEWS"})


@dataclass(frozen=True)
class TrustInfo:
    domain: str
    name: str
    bias_score: int          # -3 .. +3
    bias_label: str          # human-readable AllSides label
    factual_rating: str      # MBFC label
    trust_score: int         # 0–100
    country: str             # ISO 3166-1 alpha-2
    source: str              # "registry" | "llm" | "default"

    @property
    def is_low_trust(self) -> bool:
        return self.factual_rating in LOW_TRUST_RATINGS


def _load_registry() -> dict[str, dict]:
    try:
        with _REGISTRY_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
        return data.get("sources", {})
    except Exception:
        return {}


# Module-level cache — loaded once on first call
_registry: dict[str, dict] | None = None


def _get_registry() -> dict[str, dict]:
    global _registry
    if _registry is None:
        _registry = _load_registry()
    return _registry


def _extract_domain(url_or_domain: str) -> str:
    """Normalise a URL or bare domain to a registered-domain key (e.g. 'yle.fi')."""
    s = url_or_domain.strip()
    if "://" not in s:
        s = "https://" + s
    host = urlparse(s).hostname or ""
    host = host.lower().removeprefix("www.")
    return host


def _default_trust(domain: str) -> TrustInfo:
    return TrustInfo(
        domain=domain,
        name=domain,
        bias_score=0,
        bias_label="CENTER",
        factual_rating="MOSTLY FACTUAL",
        trust_score=60,
        country="",
        source="default",
    )


def get_source_trust(url_or_domain: str) -> TrustInfo:
    """
    Look up trust/bias data for a source domain.

    Returns a TrustInfo — never raises. Falls back to a neutral default
    when the domain is not in the registry and LLM fallback is unavailable.
    """
    domain = _extract_domain(url_or_domain)
    registry = _get_registry()

    entry = registry.get(domain)
    if entry:
        return TrustInfo(
            domain=domain,
            name=entry.get("name", domain),
            bias_score=int(entry.get("bias_score", 0)),
            bias_label=entry.get("bias_label", "CENTER"),
            factual_rating=entry.get("factual_rating", "MOSTLY FACTUAL"),
            trust_score=int(entry.get("trust_score", 60)),
            country=entry.get("country", ""),
            source="registry",
        )

    # Try LLM fallback (best-effort, does not block ingest if unavailable)
    llm_result = _llm_fallback(domain)
    if llm_result:
        return llm_result

    return _default_trust(domain)


# ---------------------------------------------------------------------------
# LLM fallback for unknown sources
# ---------------------------------------------------------------------------

def _llm_fallback(domain: str) -> TrustInfo | None:
    """
    Ask Ollama to estimate bias/trust for an unknown source domain.
    Returns None if Ollama is unavailable or the response is unparseable.
    """
    try:
        from ..services.llm import _get_ollama  # type: ignore[attr-defined]
        client = _get_ollama()
        if client is None:
            return None

        prompt = (
            f"You are a media bias expert. Rate the news source '{domain}' on two dimensions:\n"
            "1. bias: one of EXTREME-LEFT, LEFT, LEFT-CENTER, CENTER, RIGHT-CENTER, RIGHT, EXTREME-RIGHT\n"
            "2. factual_rating: one of VERY HIGH, HIGH, MOSTLY FACTUAL, MIXED, LOW, VERY LOW, FAKE NEWS\n\n"
            "Respond ONLY with a JSON object, no explanation. Example:\n"
            '{"bias": "CENTER", "factual_rating": "HIGH"}'
        )

        response = client.chat.completions.create(
            model="llama3.2",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=80,
        )

        text = (response.choices[0].message.content or "").strip()
        # Extract the first JSON object from the response
        match = re.search(r'\{[^}]+\}', text)
        if not match:
            return None

        data = json.loads(match.group())
        bias_label = data.get("bias", "CENTER").upper().strip()
        factual_rating = data.get("factual_rating", "MOSTLY FACTUAL").upper().strip()

        bias_score = _LABEL_TO_BIAS.get(bias_label, 0)
        trust_score = _RATING_TO_TRUST.get(factual_rating, 60)

        return TrustInfo(
            domain=domain,
            name=domain,
            bias_score=bias_score,
            bias_label=bias_label,
            factual_rating=factual_rating,
            trust_score=trust_score,
            country="",
            source="llm",
        )
    except Exception:
        return None
