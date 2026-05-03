import logging

from fastapi import APIRouter

from ..database import apply_feedback
from ..models import FeedbackPayload, FeedbackResponse

router = APIRouter(prefix="/api", tags=["feedback"])
log = logging.getLogger(__name__)


@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(payload: FeedbackPayload) -> FeedbackResponse:
    result = apply_feedback(payload.article_id, payload.is_relevant, dwell_ms=payload.dwell_ms)
    log.info(
        "POST /api/feedback: article_id=%d is_relevant=%s dwell_ms=%s", payload.article_id, payload.is_relevant, payload.dwell_ms
    )
    return FeedbackResponse(**result)
