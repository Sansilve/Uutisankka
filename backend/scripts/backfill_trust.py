"""
Backfill trust/bias data for all existing articles.
Uses the source registry (fast) with a default fallback for unknown sources.
Skips Ollama LLM fallback to keep runtime short.
"""
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.database import _conn
from backend.app.services.trust import _extract_domain, _get_registry, _default_trust, TrustInfo

def backfill():
    registry = _get_registry()
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id, url, source FROM articles WHERE trust_score IS NULL"
        ).fetchall()

        print(f"Backfillattavana: {len(rows)} artikkelia")

        updates = []
        hit = 0
        miss = 0

        for row in rows:
            domain = _extract_domain(row["url"] or "")

            entry = registry.get(domain) if domain else None
            if entry:
                t = TrustInfo(
                    domain=domain,
                    name=entry.get("name", domain),
                    bias_score=entry.get("bias_score", 0),
                    bias_label=entry.get("bias_label", "CENTER"),
                    factual_rating=entry.get("factual_rating", "MOSTLY FACTUAL"),
                    trust_score=entry.get("trust_score", 60),
                    country=entry.get("country", ""),
                    source="registry",
                )
                hit += 1
            else:
                t = _default_trust(domain or "unknown")
                miss += 1

            updates.append((
                t.trust_score,
                t.bias_score,
                t.factual_rating,
                "unknown",  # fact_check_status
                row["id"],
            ))

        conn.executemany(
            """UPDATE articles
               SET trust_score = ?,
                   bias_score  = ?,
                   factual_rating = ?,
                   fact_check_status = ?
               WHERE id = ?""",
            updates,
        )
        conn.commit()
        print(f"Valmis: {hit} rekisteristä, {miss} oletusarvoilla")
        print(f"Yhteensä päivitetty: {len(updates)}")
    finally:
        conn.close()

if __name__ == "__main__":
    backfill()
