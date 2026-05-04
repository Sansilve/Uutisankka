"""
benchmark_ollama.py — Compare Ollama models on real Finnish articles from DB.

Usage:
    python backend/scripts/benchmark_ollama.py [--models llama3.2 mistral:7b] [--n 10]

Reads N articles from the DB that have been enriched (have summary_json),
runs summarize_article / translate_and_summarize on raw content for each model,
and prints a side-by-side quality comparison with timing.
"""

import argparse
import os
import sys
import time
import json

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.database import _conn
from backend.app.services.ingest import summarize_article, translate_and_summarize, is_english_url


def fetch_sample_articles(n: int) -> list[dict]:
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT id, title, url, content, source
            FROM articles
            WHERE summary_json IS NOT NULL AND content IS NOT NULL AND length(content) > 200
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (n,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def run_model(model: str, articles: list[dict]) -> list[dict]:
    os.environ["OLLAMA_MODEL"] = model
    # Reload config so the model change takes effect
    import importlib
    import backend.app.config as cfg
    importlib.reload(cfg)
    import backend.app.services.llm as llm_mod
    importlib.reload(llm_mod)
    import backend.app.services.summarizer as sum_mod
    importlib.reload(sum_mod)
    import backend.app.services.translator as trans_mod
    importlib.reload(trans_mod)
    import backend.app.services.ingest as ing_mod
    importlib.reload(ing_mod)

    results = []
    for art in articles:
        t0 = time.perf_counter()
        try:
            if is_english_url(art["url"]):
                fin_title, summary = ing_mod.translate_and_summarize(art["title"], art["content"])
            else:
                fin_title = None
                summary = ing_mod.summarize_article(art["title"], art["content"], art["source"])
        except Exception as e:
            fin_title = None
            summary = {"error": str(e)}
        elapsed = round(time.perf_counter() - t0, 2)
        results.append(
            {
                "id": art["id"],
                "original_title": art["title"],
                "translated_title": fin_title,
                "summary": summary,
                "elapsed_s": elapsed,
            }
        )
    return results


def print_comparison(models: list[str], all_results: dict[str, list[dict]]) -> None:
    articles = all_results[models[0]]
    separator = "=" * 80

    for i, art in enumerate(articles):
        print(f"\n{separator}")
        print(f"Article {i+1} | ID={art['id']}")
        print(f"Original title: {art['original_title']}")
        for model in models:
            r = all_results[model][i]
            print(f"\n  [{model}] ({r['elapsed_s']}s)")
            if r["translated_title"]:
                print(f"  Finnish title: {r['translated_title']}")
            bullets = r["summary"].get("bullets") or r["summary"].get("items") or []
            if bullets:
                for b in bullets[:3]:
                    print(f"    • {b}")
            elif "error" in r["summary"]:
                print(f"  ERROR: {r['summary']['error']}")

    print(f"\n{separator}")
    print("Timing summary:")
    for model in models:
        times = [r["elapsed_s"] for r in all_results[model]]
        avg = round(sum(times) / len(times), 2)
        total = round(sum(times), 2)
        print(f"  {model}: avg={avg}s  total={total}s  ({len(times)} articles)")


def main():
    parser = argparse.ArgumentParser(description="Benchmark Ollama models on Finnish articles")
    parser.add_argument("--models", nargs="+", default=["llama3.2", "mistral:7b"],
                        help="Models to compare (default: llama3.2 mistral:7b)")
    parser.add_argument("--n", type=int, default=10,
                        help="Number of articles to test (default: 10)")
    args = parser.parse_args()

    print(f"Fetching {args.n} sample articles from DB...")
    articles = fetch_sample_articles(args.n)
    if not articles:
        print("No enriched articles found in DB. Run ingest first.")
        sys.exit(1)
    print(f"Got {len(articles)} articles.")

    all_results: dict[str, list[dict]] = {}
    for model in args.models:
        print(f"\nRunning model: {model} ...")
        all_results[model] = run_model(model, articles)

    print_comparison(args.models, all_results)

    # Save raw results to JSON for further analysis
    out_path = os.path.join(os.path.dirname(__file__), "benchmark_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"models": args.models, "results": all_results}, f, ensure_ascii=False, indent=2)
    print(f"\nRaw results saved to: {out_path}")


if __name__ == "__main__":
    main()
