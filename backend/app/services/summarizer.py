import re
from collections import Counter


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 25]


def _extract_entities(text: str) -> list[str]:
    matches = re.findall(r"\b[A-Z][a-zA-Z\-]{2,}\b", text)
    counts = Counter(matches)
    common = [item for item, _ in counts.most_common(4)]
    return common


def summarize_article(title: str, content: str) -> dict[str, list[str]]:
    sentences = _split_sentences(content)

    if not sentences:
        return {
            "bullets": [
                f"What happened: {title}",
                "Why it matters: Potentially relevant development with limited details in feed text.",
                "Key entities involved: Not enough extracted context.",
            ]
        }

    lead = sentences[0]
    impact_sentence = next(
        (
            s
            for s in sentences
            if any(token in s.lower() for token in ["because", "impact", "risk", "market", "policy", "economy"])
        ),
        sentences[min(1, len(sentences) - 1)],
    )

    entities = _extract_entities(f"{title}. {' '.join(sentences[:4])}")
    entities_line = ", ".join(entities) if entities else "Not clearly identified in snippet"

    bullets = [
        f"What happened: {lead}",
        f"Why it matters: {impact_sentence}",
        f"Key entities involved: {entities_line}.",
    ]

    extra = [s for s in sentences[1:5] if s not in {lead, impact_sentence}]
    for sentence in extra[:2]:
        bullets.append(f"Context: {sentence}")

    return {"bullets": bullets[:5]}
