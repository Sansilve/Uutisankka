import json
import logging

from fastapi import APIRouter, Query

from ..config import SCORING_VERSION
from ..database import (
    count_articles,
    get_preferences,
    get_article_facets,
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
    result["scoring_version"] = SCORING_VERSION
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


@router.get("/articles/stats")
def get_articles_stats() -> dict:
    """Return real aggregate counts for the stat panel (total, by region, paywall)."""
    prefs = get_preferences()
    return count_articles(
        region_filters=_scope_to_regions(prefs),
        hide_paywall=False,
        excluded_sources=prefs.get("excluded_sources") or None,
    )


@router.get("/articles", response_model=AllNewsResponse)
def get_all_articles(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    include_paywall: bool = Query(default=False),
    scopes: list[str] = Query(default_factory=lambda: ["suomi", "maailma", "paikalliset"]),
    local_cities: list[str] = Query(default_factory=list),
    categories: list[str] = Query(default_factory=list),
    sources: list[str] = Query(default_factory=list),
    tones: list[str] = Query(default_factory=list),
) -> AllNewsResponse:
    """Development endpoint: browse all latest articles."""
    prefs = get_preferences()
    hide_paywall = False if include_paywall else prefs.get("hide_paywall", True)
    excluded_sources = prefs.get("excluded_sources") or None

    rows = list_articles(
        limit=limit,
        offset=offset,
        region_filters=None,
        hide_paywall=hide_paywall,
        excluded_sources=excluded_sources,
        scope_filters=scopes,
        local_cities=local_cities,
        source_filters=sources,
        category_filters=categories,
        tone_filters=tones,
    )
    stats = count_articles(
        region_filters=None,
        hide_paywall=hide_paywall,
        excluded_sources=excluded_sources,
        scope_filters=scopes,
        local_cities=local_cities,
        source_filters=sources,
        category_filters=categories,
        tone_filters=tones,
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
                score=float(row["score"] or 0.0),
                category=row["category"],
                category_secondary=row["category_secondary"],
                tone=row["tone"],
            )
        )
    log.info("GET /api/articles limit=%d include_paywall=%s → %d items", limit, include_paywall, len(items))
    return AllNewsResponse(total=int(stats.get("total", len(items))), items=items)


@router.get("/articles/facets")
def get_all_articles_facets(
    include_paywall: bool = Query(default=False),
    scopes: list[str] = Query(default_factory=lambda: ["suomi", "maailma", "paikalliset"]),
    local_cities: list[str] = Query(default_factory=list),
) -> dict:
    prefs = get_preferences()
    return get_article_facets(
        hide_paywall=False if include_paywall else prefs.get("hide_paywall", True),
        excluded_sources=prefs.get("excluded_sources") or None,
        scope_filters=scopes,
        local_cities=local_cities,
    )
