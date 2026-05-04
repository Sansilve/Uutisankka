import logging

from fastapi import APIRouter, BackgroundTasks

from ..database import (
    get_preferences,
    reset_all_enrichment,
)
from ..services.ingest import (
    enrich_unprocessed_articles,
    get_last_ingest_stats,
    rescore_all,
    rescore_for_topics,
)
from ..services.llm import get_llm_stats

router = APIRouter(prefix="/api/admin", tags=["admin"])
log = logging.getLogger(__name__)

# Simple in-memory flag so the frontend can poll reenrich progress.
_reenrich_status: dict[str, str | int] = {"state": "idle", "enriched": 0}


def _reenrich_changed(changed_topics: list[str], preferences: dict) -> None:
    global _reenrich_status
    _reenrich_status = {"state": "running", "enriched": 0}
    log.info("_reenrich_changed: starting (changed_topics=%s)", changed_topics)
    if changed_topics:
        enriched = rescore_for_topics(changed_topics, preferences)
    else:
        reset_all_enrichment()
        enriched = rescore_all(preferences)
    _reenrich_status = {"state": "done", "enriched": enriched}
    log.info("_reenrich_changed: done, enriched=%d", enriched)


@router.post("/reenrich")
def admin_reenrich(background_tasks: BackgroundTasks) -> dict[str, str]:
    """Trigger a full re-score in the background. Poll /api/admin/reenrich/status."""
    if _reenrich_status["state"] == "running":
        return {"state": "already_running"}
    log.info("POST /api/admin/reenrich: triggering full rescore")
    background_tasks.add_task(_reenrich_changed, [], get_preferences())
    return {"state": "started"}


@router.post("/resummarize")
def admin_resummarize(background_tasks: BackgroundTasks) -> dict[str, str]:
    """Reset all summaries so they get regenerated with the current prompt."""
    import sqlite3
    from ..database import _conn, _db_lock

    def _do_resummarize() -> None:
        log.info("admin_resummarize: resetting all summaries")
        with _db_lock:
            conn = _conn()
            try:
                conn.execute("UPDATE articles SET summary_json = '{\"bullets\": []}'")
                conn.commit()
            finally:
                conn.close()
        enrich_unprocessed_articles()
        log.info("admin_resummarize: done")

    background_tasks.add_task(_do_resummarize)
    return {"state": "started"}


@router.get("/reenrich/status")
def reenrich_status() -> dict[str, str | int]:
    return _reenrich_status


@router.get("/llm-stats")
def llm_stats() -> dict[str, dict[str, int | float]]:
    return get_llm_stats()


@router.get("/ingest-stats")
def ingest_stats() -> dict:
    from ..config import (
        OBSERVABILITY_LLM_REJECTION_THRESHOLD,
        OBSERVABILITY_PAYWALL_FP_THRESHOLD,
        OBSERVABILITY_TRANSLATION_FALLBACK_THRESHOLD,
    )

    stats = get_last_ingest_stats()
    llm_stats = get_llm_stats()
    alerts: list[str] = []
    total = stats.get("translated_llm", 0) + stats.get("translated_heuristic", 0) + stats.get("paywall_detected", 0)
    if total > 0:
        paywall_rate = stats.get("paywall_detected", 0) / total
        if paywall_rate > OBSERVABILITY_PAYWALL_FP_THRESHOLD:
            alerts.append(f"Paywall false-positive rate high ({paywall_rate:.0%} > {OBSERVABILITY_PAYWALL_FP_THRESHOLD:.0%})")
            log.warning("ALERT: paywall_false_positive_rate=%.2f exceeds threshold=%.2f", paywall_rate, OBSERVABILITY_PAYWALL_FP_THRESHOLD)
        llm_total = stats.get("translated_llm", 0) + stats.get("translated_heuristic", 0)
        if llm_total > 0:
            fallback_rate = stats.get("translated_heuristic", 0) / llm_total
            if fallback_rate > OBSERVABILITY_TRANSLATION_FALLBACK_THRESHOLD:
                alerts.append(f"Translation LLM fallback rate high ({fallback_rate:.0%} > {OBSERVABILITY_TRANSLATION_FALLBACK_THRESHOLD:.0%})")
                log.warning("ALERT: translation_fallback_rate=%.2f exceeds threshold=%.2f", fallback_rate, OBSERVABILITY_TRANSLATION_FALLBACK_THRESHOLD)

    llm_calls = 0
    llm_rejections = 0
    for provider_stats in llm_stats.values():
        llm_calls += int(provider_stats.get("calls", 0))
        llm_rejections += int(provider_stats.get("validation_rejections", 0))

    if llm_calls > 0:
        llm_rejection_rate = llm_rejections / llm_calls
        if llm_rejection_rate > OBSERVABILITY_LLM_REJECTION_THRESHOLD:
            alerts.append(
                f"LLM validation rejection rate high ({llm_rejection_rate:.0%} > {OBSERVABILITY_LLM_REJECTION_THRESHOLD:.0%})"
            )
            log.warning(
                "ALERT: llm_rejection_rate=%.2f exceeds threshold=%.2f",
                llm_rejection_rate,
                OBSERVABILITY_LLM_REJECTION_THRESHOLD,
            )
    return {**stats, "alerts": alerts}
