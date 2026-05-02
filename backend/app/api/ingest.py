import logging

from fastapi import APIRouter

from ..models import IngestResponse
from ..services.ingest import ingest_feeds

router = APIRouter(prefix="/api", tags=["ingest"])
log = logging.getLogger(__name__)


@router.post("/ingest", response_model=IngestResponse)
def trigger_ingest() -> IngestResponse:
    log.info("POST /api/ingest: manual ingest triggered")
    result = ingest_feeds()
    log.info("POST /api/ingest: done – %s", result)
    return IngestResponse(**result)
