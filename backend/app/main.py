"""
UutisAnkka – FastAPI application entry point.

Responsibility of this module:
  - Configure structured logging
  - Instantiate the FastAPI app
  - Register CORS middleware
  - Mount all domain routers (api/)
  - Register global exception handler
  - Manage application lifespan (DB init, background ingest)
"""
import asyncio
import contextlib
import logging
import logging.config
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.admin import router as admin_router
from .api.articles import router as articles_router
from .api.briefing import router as briefing_router
from .api.errors import unhandled_exception_handler
from .api.feedback import router as feedback_router
from .api.ingest import router as ingest_router
from .api.preferences import router as preferences_router
from .database import ensure_default_preferences, init_db
from .services.ingest import ingest_feeds

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            }
        },
        "root": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
        },
    }
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CORS origins (extend via CORS_ALLOW_ORIGINS env var, comma-separated)
# ---------------------------------------------------------------------------

_DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "http://localhost:8082",
    "http://127.0.0.1:8082",
]

_extra = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if o.strip()]
CORS_ORIGINS = _DEFAULT_ORIGINS + _extra

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

background_task: asyncio.Task | None = None


async def _periodic_ingest() -> None:
    loop = asyncio.get_event_loop()
    interval = int(os.getenv("INGEST_INTERVAL_SECONDS", str(30 * 60)))
    while True:
        try:
            log.info("periodic_ingest: starting scheduled run")
            await loop.run_in_executor(None, ingest_feeds)
        except Exception as exc:
            log.error("periodic_ingest: error – %s", exc)
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global background_task
    log.info("startup: initialising database")
    init_db()
    ensure_default_preferences()
    background_task = asyncio.create_task(_periodic_ingest())
    log.info(
        "startup: periodic ingest scheduled (interval=%s s)",
        os.getenv("INGEST_INTERVAL_SECONDS", str(30 * 60)),
    )
    yield
    log.info("shutdown: cancelling background tasks")
    if background_task:
        background_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await background_task


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="UutisAnkka API",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=os.getenv("CORS_ALLOW_ORIGIN_REGEX") or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, unhandled_exception_handler)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(briefing_router)
app.include_router(preferences_router)
app.include_router(feedback_router)
app.include_router(articles_router)
app.include_router(ingest_router)
app.include_router(admin_router)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}

