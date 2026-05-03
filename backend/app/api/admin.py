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
def ingest_stats() -> dict[str, int]:
    return get_last_ingest_stats()
