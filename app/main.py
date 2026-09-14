"""FastAPI application entry point.

STEP 1 of the build: app skeleton + a plain health check only. Dense
search, sparse search, and the /retrieve endpoint are added in later
steps — this file grows as each service is wired in, not all at once.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(title=settings.api_title, version=settings.api_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    """Basic liveness check — confirms the API process itself is up.
    Does NOT check ChromaDB or the sparse index; those get their own
    /health/dense and /health/sparse checks once those services exist
    (Steps 2 and 3)."""
    return {"status": "ok", "service": settings.api_title}


@app.on_event("startup")
async def on_startup() -> None:
    logger.info(f"{settings.api_title} v{settings.api_version} starting up")
