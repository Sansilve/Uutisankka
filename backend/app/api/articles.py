import json
import logging

from fastapi import APIRouter, Query

from ..database import (
    get_preferences,
    get_swipe_history,
    list_articles,
    top_feedback_metrics,
)
from ..models import AllNewsItem, AllNewsResponse, MetricsResponse, HistoryResponse, SwipeHistoryItem
from .briefing import _scope_to_regions

router = APIRouter(prefix="/api", tags=["articles"])
log = logging.getLogger(__name__)


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(limit: int = Query(default=10, ge=1, le=20)) -> MetricsResponse:
    result = top_feedback_metrics(limit)
    return MetricsResponse(**result)


@router.get("/history", response_model=HistoryResponse)
def get_history(limit: int = Query(default=100, ge=1, le=500)) -> HistoryResponse:
    rows = get_swipe_history(limit)
    items = []
    for row in rows:
        items.append(
            SwipeHistoryItem(
                swipe_id=row["swipe_id"],
                is_relevant=bool(row["is_relevant"]),
                swiped_at=row["swiped_at"],
                id=row["id"],
                title=row["title"],
                source=row["source"],
                published_at=row["published_at"],
                url=row["url"],
                topics=json.loads(row["topics"] or "[]"),
                summary=json.loads(row["summary_json"] or '{"bullets": []}'),
            )
        )
    log.info("GET /api/history limit=%d → %d items", limit, len(items))
    return HistoryResponse(total=len(items), items=items)


@router.get("/articles", response_model=AllNewsResponse)
def get_all_articles(
    limit: int = Query(default=300, ge=1, le=1000),
    include_paywall: bool = Query(default=False),
) -> AllNewsResponse:
    """Development endpoint: browse all latest articles."""
    prefs = get_preferences()
    rows = list_articles(
        limit=limit,
        region_filters=_scope_to_regions(prefs),
        hide_paywall=False if include_paywall else prefs.get("hide_paywall", True),
        excluded_sources=prefs.get("excluded_sources") or None,
    )
    items: list[AllNewsItem] = []
    for row in rows:
        items.append(
            AllNewsItem(
                id=row["id"],
                title=row["title"],
                source=row["source"],
                region=row["region"],
                published_at=row["published_at"],
                url=row["url"],
                topics=json.loads(row["topics"] or "[]"),
                summary=json.loads(row["summary_json"] or '{"bullets": []}'),
                is_paywall=bool(row["is_paywall"]),
            )
        )
    log.info("GET /api/articles limit=%d include_paywall=%s → %d items", limit, include_paywall, len(items))
    return AllNewsResponse(total=len(items), items=items)
