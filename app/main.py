"""FastAPI application entry point.

STEP 1 of the build: app skeleton + a plain health check only. Dense
search, sparse search, and the /retrieve endpoint are added in later
steps — this file grows as each service is wired in, not all at once.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.exceptions import DenseSearchError
from app.logger import get_logger
from app.services.dense_search import DenseSearchService

logger = get_logger(__name__)

app = FastAPI(title=settings.api_title, version=settings.api_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Loaded once at startup (see on_startup below), never per-request —
# holding it as a module-level singleton is what makes that possible.
dense_service: DenseSearchService | None = None


@app.get("/health")
async def health() -> dict:
    """Basic liveness check — confirms the API process itself is up.
    Does NOT check ChromaDB or the sparse index; those get their own
    /health/dense and /health/sparse checks."""
    return {"status": "ok", "service": settings.api_title}


@app.get("/health/dense")
async def health_dense() -> dict:
    """Proves the ChromaDB connection is real by counting chunks in the
    collection — not just that the client object was constructed."""
    if dense_service is None:
        raise HTTPException(
            status_code=503, detail="Dense search service not initialized"
        )
    try:
        count = dense_service.count()
    except DenseSearchError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "status": "ok",
        "collection": settings.chroma_collection_name,
        "chunk_count": count,
    }


@app.on_event("startup")
async def on_startup() -> None:
    global dense_service
    logger.info(f"{settings.api_title} v{settings.api_version} starting up")
    dense_service = DenseSearchService()
