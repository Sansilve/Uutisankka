import json
import logging
from datetime import datetime

from fastapi import APIRouter, Query

from ..config import LOCAL_CITIES
from ..database import (
    count_articles,
    get_preferences,
    random_briefing,
    top_briefing,
)
from ..models import ArticleBrief, BriefingResponse, ScoreBreakdownPayload, SummaryPayload

router = APIRouter(prefix="/api", tags=["briefing"])
log = logging.getLogger(__name__)


def _scope_to_regions(prefs: dict) -> list[str] | None:
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


def rows_to_briefing(rows, empty_reason: str | None = None) -> BriefingResponse:
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
                is_paywall=bool(row["is_paywall"]),
                category=row["category"] if "category" in row.keys() else None,
                category_secondary=row["category_secondary"] if "category_secondary" in row.keys() else None,
                tone=row["tone"] if "tone" in row.keys() else None,
                tone_confidence=row["tone_confidence"] if "tone_confidence" in row.keys() else None,
                tone_reason=row["tone_reason"] if "tone_reason" in row.keys() else None,
            )
        )
    return BriefingResponse(
        generated_at=datetime.utcnow(),
        total=len(stories),
        stories=stories,
        empty_reason=empty_reason,
    )


@router.get("/briefing", response_model=BriefingResponse)
def get_briefing(limit: int = Query(default=10, ge=1, le=50)) -> BriefingResponse:
    prefs = get_preferences()
    scope_regions = _scope_to_regions(prefs)
    hide_paywall = prefs.get("hide_paywall", True)
    excluded_sources = prefs.get("excluded_sources") or None
    tone_filter = prefs.get("tone_filter", "all")

    rows = top_briefing(
        limit,
        region_filters=scope_regions,
        hide_paywall=hide_paywall,
        excluded_sources=excluded_sources,
        tone_filter=tone_filter,
    )

    empty_reason: str | None = None
    if not rows:
        all_total = count_articles().get("total", 0)
        if all_total == 0:
            empty_reason = "no_data"
        else:
            in_scope_total = count_articles(
                region_filters=scope_regions,
                hide_paywall=False,
                excluded_sources=None,
            ).get("total", 0)
            if in_scope_total == 0:
                empty_reason = "no_scope_match"
            elif hide_paywall:
                open_total = count_articles(
                    region_filters=scope_regions,
                    hide_paywall=True,
                    excluded_sources=excluded_sources,
                    tone_filters=[tone_filter] if tone_filter != "all" else None,
                ).get("total", 0)
                if open_total == 0:
                    empty_reason = "only_paywalled"
            if empty_reason is None:
                empty_reason = "no_filter_match"

    log.info("GET /api/briefing limit=%d → %d stories", limit, len(rows))
    return rows_to_briefing(rows, empty_reason=empty_reason)


@router.get("/briefing/random", response_model=BriefingResponse)
def get_random_briefing(limit: int = Query(default=10, ge=1, le=50)) -> BriefingResponse:
    prefs = get_preferences()
    rows = random_briefing(
        limit,
        region_filters=_scope_to_regions(prefs),
        hide_paywall=prefs.get("hide_paywall", True),
        excluded_sources=prefs.get("excluded_sources") or None,
    )
    log.info("GET /api/briefing/random limit=%d → %d stories", limit, len(rows))
    return rows_to_briefing(rows)
