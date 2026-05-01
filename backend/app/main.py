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
    init_db,
    random_briefing,
    reset_all_enrichment,
    top_briefing,
    top_feedback_metrics,
    upsert_preferences,
)
from .models import (
    ArticleBrief,
    BriefingResponse,
    FeedbackPayload,
    FeedbackResponse,
    IngestResponse,
    MetricsResponse,
    PreferenceProfile,
    PreferenceUpdate,
    ScoreBreakdownPayload,
    SummaryPayload,
)
from .services.ingest import enrich_unprocessed_articles, ingest_feeds

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
    background_task = asyncio.create_task(periodic_ingest())
    yield
    if background_task:
        background_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await background_task


app = FastAPI(title="No-BS Finnish News Briefing", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
    upsert_preferences(payload.interests, payload.disliked_topics)
    # Run re-scoring in the background so the HTTP response returns immediately.
    background_tasks.add_task(_reenrich_all)
    return PreferenceProfile(**get_preferences())


def _reenrich_all() -> None:
    global _reenrich_status
    _reenrich_status = {"state": "running", "enriched": 0}
    reset_all_enrichment()
    enriched = enrich_unprocessed_articles()
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


@app.get("/api/briefing", response_model=BriefingResponse)
def get_briefing(limit: int = Query(default=10, ge=1, le=50)) -> BriefingResponse:
    return _rows_to_briefing(top_briefing(limit))


@app.get("/api/briefing/random", response_model=BriefingResponse)
def get_random_briefing(limit: int = Query(default=10, ge=1, le=50)) -> BriefingResponse:
    return _rows_to_briefing(random_briefing(limit))


@app.post("/api/admin/reenrich")
def admin_reenrich(background_tasks: BackgroundTasks) -> dict[str, str]:
    """Trigger a full re-score in the background. Poll /api/admin/reenrich/status."""
    if _reenrich_status["state"] == "running":
        return {"state": "already_running"}
    background_tasks.add_task(_reenrich_all)
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
