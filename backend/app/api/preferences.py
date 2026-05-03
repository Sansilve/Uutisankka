import logging

from fastapi import APIRouter, BackgroundTasks

from ..database import (
    get_preferences,
    upsert_preferences,
)
from ..models import PreferenceProfile, PreferenceUpdate
from .admin import _reenrich_changed

router = APIRouter(prefix="/api", tags=["preferences"])
log = logging.getLogger(__name__)


def _diff_topics(old: dict, new: dict) -> list[str]:
    old_set = set(old.get("interests", [])) | set(old.get("disliked_topics", []))
    new_set = set(new.get("interests", [])) | set(new.get("disliked_topics", []))
    return list(old_set.symmetric_difference(new_set))


@router.get("/preferences", response_model=PreferenceProfile)
def read_preferences() -> PreferenceProfile:
    return PreferenceProfile(**get_preferences())


@router.put("/preferences", response_model=PreferenceProfile)
def update_preferences(
    payload: PreferenceUpdate, background_tasks: BackgroundTasks
) -> PreferenceProfile:
    old_prefs = get_preferences()
    upsert_preferences(
        payload.interests,
        payload.disliked_topics,
        news_scope=payload.news_scope,
        local_city=payload.local_city,
        hide_paywall=payload.hide_paywall,
        excluded_sources=payload.excluded_sources,
        tone_filter=payload.tone_filter,
    )
    new_prefs = get_preferences()
    changed_topics = _diff_topics(old_prefs, new_prefs)
    log.info(
        "PUT /api/preferences: changed_topics=%s, triggering targeted reenrich", changed_topics
    )
    background_tasks.add_task(_reenrich_changed, changed_topics, new_prefs)
    return PreferenceProfile(**new_prefs)
