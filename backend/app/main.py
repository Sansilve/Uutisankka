import asyncio
import contextlib
import json
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import BackgroundTasks, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .database import (
    apply_feedback,
    ensure_default_preferences,
    get_preferences,
    get_swipe_history,
    init_db,
    random_briefing,
    reset_all_enrichment,
    top_briefing,
    top_feedback_metrics,
    upsert_preferences,
)
from .config import LOCAL_CITIES
from .models import (
    ArticleBrief,
    BriefingResponse,
    FeedbackPayload,
    FeedbackResponse,
    HistoryResponse,
    IngestResponse,
    MetricsResponse,
    PreferenceProfile,
    PreferenceUpdate,
    ScoreBreakdownPayload,
    SummaryPayload,
    SwipeHistoryItem,
)
from .services.ingest import enrich_unprocessed_articles, ingest_feeds, rescore_all, rescore_for_topics, translate_existing_english

import threading

# Simple in-memory flag so the frontend can poll reenrich progress.
_reenrich_status: dict[str, str | int] = {"state": "idle", "enriched": 0}


async def periodic_ingest() -> None:
    while True:
        try:
            ingest_feeds()
        except Exception:
            # Keep the loop alive even if one feed cycle fails.
            pass
        await asyncio.sleep(30 * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global background_task
    init_db()
    ensure_default_preferences()
    enrich_unprocessed_articles()
    # Translate any English articles that were stored before this feature was added
    asyncio.get_event_loop().run_in_executor(None, translate_existing_english)
    background_task = asyncio.create_task(periodic_ingest())
    yield
    if background_task:
        background_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await background_task


app = FastAPI(title="No-BS Finnish News Briefing", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://192.168.10.50:8081",
        "http://localhost:8082",
        "http://127.0.0.1:8082",
        "http://192.168.10.50:8082",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/ingest", response_model=IngestResponse)
def trigger_ingest() -> IngestResponse:
    return IngestResponse(**ingest_feeds())


@app.get("/api/preferences", response_model=PreferenceProfile)
def read_preferences() -> PreferenceProfile:
    return PreferenceProfile(**get_preferences())


@app.put("/api/preferences", response_model=PreferenceProfile)
def update_preferences(payload: PreferenceUpdate, background_tasks: BackgroundTasks) -> PreferenceProfile:
    old_prefs = get_preferences()
    upsert_preferences(
        payload.interests,
        payload.disliked_topics,
        news_scope=payload.news_scope,
        local_city=payload.local_city,
    )
    new_prefs = get_preferences()
    changed_topics = _diff_topics(old_prefs, new_prefs)
    background_tasks.add_task(_reenrich_changed, changed_topics, new_prefs)
    return PreferenceProfile(**new_prefs)


def _diff_topics(old: dict, new: dict) -> list[str]:
    """Return the topic IDs that were added or removed in either interests or dislikes."""
    old_set = set(old.get("interests", [])) | set(old.get("disliked_topics", []))
    new_set = set(new.get("interests", [])) | set(new.get("disliked_topics", []))
    return list(old_set.symmetric_difference(new_set))


def _reenrich_changed(changed_topics: list[str], preferences: dict) -> None:
    """Targeted rescore: only articles affected by the changed topics.
    Falls back to full rescore+reset when called from the admin endpoint (empty changed_topics)."""
    global _reenrich_status
    _reenrich_status = {"state": "running", "enriched": 0}
    if changed_topics:
        enriched = rescore_for_topics(changed_topics, preferences)
    else:
        # Admin-triggered or first run: full rescore
        reset_all_enrichment()
        enriched = rescore_all(preferences)
    _reenrich_status = {"state": "done", "enriched": enriched}


def _rows_to_briefing(rows) -> BriefingResponse:
    stories: list[ArticleBrief] = []
    for row in rows:
        summary = json.loads(row["summary_json"]) if row["summary_json"] else {"bullets": []}
        topics = json.loads(row["topics"]) if row["topics"] else []
        score_breakdown = (
            json.loads(row["score_breakdown_json"])
            if row["score_breakdown_json"]
            else {"items": []}
        )
        stories.append(
            ArticleBrief(
                id=row["id"],
                title=row["title"],
                source=row["source"],
                published_at=row["published_at"],
                url=row["url"],
                score=row["score"],
                base_score=row["base_score"],
                feedback_score=row["feedback_score"],
                feedback_positive=row["feedback_positive"],
                feedback_negative=row["feedback_negative"],
                topics=topics,
                summary=SummaryPayload(**summary),
                score_breakdown=ScoreBreakdownPayload(**score_breakdown),
            )
        )
    return BriefingResponse(generated_at=datetime.utcnow(), total=len(stories), stories=stories)


def _scope_to_regions(prefs: dict) -> list[str] | None:
    """Convert news_scope + local_city preference to region filter list for DB queries."""
    scope: list[str] = prefs.get("news_scope") or ["suomi", "maailma"]
    city: str = prefs.get("local_city") or ""
    regions: list[str] = []
    for s in scope:
        if s == "suomi":
            regions.append("suomi")
        elif s == "maailma":
            regions.append("maailma")
        elif s == "paikalliset" and city in LOCAL_CITIES:
            regions.append(f"paikalliset:{city}")
    return regions if regions else None


@app.get("/api/briefing", response_model=BriefingResponse)
def get_briefing(limit: int = Query(default=10, ge=1, le=50)) -> BriefingResponse:
    prefs = get_preferences()
    return _rows_to_briefing(top_briefing(limit, region_filters=_scope_to_regions(prefs)))


@app.get("/api/briefing/random", response_model=BriefingResponse)
def get_random_briefing(limit: int = Query(default=10, ge=1, le=50)) -> BriefingResponse:
    prefs = get_preferences()
    return _rows_to_briefing(random_briefing(limit, region_filters=_scope_to_regions(prefs)))


@app.post("/api/admin/reenrich")
def admin_reenrich(background_tasks: BackgroundTasks) -> dict[str, str]:
    """Trigger a full re-score in the background. Poll /api/admin/reenrich/status."""
    if _reenrich_status["state"] == "running":
        return {"state": "already_running"}
    background_tasks.add_task(_reenrich_changed, [], get_preferences())  # [] = full rescore
    return {"state": "started"}


@app.get("/api/admin/reenrich/status")
def reenrich_status() -> dict[str, str | int]:
    return _reenrich_status


@app.post("/api/feedback", response_model=FeedbackResponse)
def submit_feedback(payload: FeedbackPayload) -> FeedbackResponse:
    result = apply_feedback(payload.article_id, payload.is_relevant)
    return FeedbackResponse(**result)


@app.get("/api/metrics", response_model=MetricsResponse)
def get_metrics(limit: int = Query(default=10, ge=1, le=20)) -> MetricsResponse:
    result = top_feedback_metrics(limit)
    return MetricsResponse(**result)
