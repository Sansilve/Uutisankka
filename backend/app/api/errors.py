"""
Standardized error handling for the UutisAnkka API.

All unhandled exceptions are caught and returned as:
    {
        "detail": "<human-readable message>",
        "error_code": "<SCREAMING_SNAKE_CASE>"
    }
"""
import logging

from fastapi import Request
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error. Please try again later.",
            "error_code": "INTERNAL_SERVER_ERROR",
        },
    )


def error_response(detail: str, error_code: str, status_code: int = 400) -> JSONResponse:
    """Helper for returning a structured error from a route handler."""
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "error_code": error_code},
    )
