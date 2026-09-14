"""FastAPI application entry point.

Grows as each build step wires in a new service — dense search (Step 2),
sparse search (Step 3), the fused /retrieve endpoint (Step 4), reranking
(Step 5). See README.md's build-status checklist for what's done.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.exceptions import DenseSearchError, SparseSearchError
from app.logger import get_logger
from app.schemas import ChunkResponse, RetrievalRequest
from app.services.dense_search import DenseSearchService
from app.services.hybrid_fusion import reciprocal_rank_fusion
from app.services.sparse_search import SparseSearchService

logger = get_logger(__name__)

app = FastAPI(title=settings.api_title, version=settings.api_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Loaded once at startup (see on_startup below), never per-request —
# holding them as module-level singletons is what makes that possible.
dense_service: DenseSearchService | None = None
sparse_service: SparseSearchService | None = None


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


@app.get("/health/sparse")
async def health_sparse() -> dict:
    """Proves the FTS5 index actually has rows — not just that the .db
    file exists on disk."""
    if sparse_service is None:
        raise HTTPException(
            status_code=503, detail="Sparse search service not initialized"
        )
    try:
        count = sparse_service.count()
    except SparseSearchError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ok", "db_path": settings.sparse_db_path, "row_count": count}


@app.post("/api/v1/retrieve", response_model=list[ChunkResponse])
async def retrieve(request: RetrievalRequest) -> list[ChunkResponse]:
    if dense_service is None or sparse_service is None:
        raise HTTPException(status_code=503, detail="Search services not initialized")

    try:
        dense_results = dense_service.search(
            request.query, top_k=settings.dense_top_k
        )
    except DenseSearchError as exc:
        raise HTTPException(status_code=503, detail=f"Dense search failed: {exc}") from exc

    try:
        sparse_results = sparse_service.search(
            request.query, top_k=settings.sparse_top_k
        )
    except SparseSearchError as exc:
        raise HTTPException(status_code=503, detail=f"Sparse search failed: {exc}") from exc

    fused = reciprocal_rank_fusion(dense_results, sparse_results)
    return fused[: request.top_k]


@app.on_event("startup")
async def on_startup() -> None:
    global dense_service, sparse_service
    logger.info(f"{settings.api_title} v{settings.api_version} starting up")
    dense_service = DenseSearchService()
    sparse_service = SparseSearchService()
