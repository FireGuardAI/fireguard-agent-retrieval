from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.exceptions import DenseSearchError, RerankError, SparseSearchError
from app.logger import get_logger
from app.schemas import ChunkResponse, RetrievalRequest
from app.services.dense_search import DenseSearchService
from app.services.hybrid_fusion import reciprocal_rank_fusion
from app.services.reranker import RerankerService
from app.services.sparse_search import SparseSearchService

logger = get_logger(__name__)

app = FastAPI(title=settings.api_title, version=settings.api_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

dense_service: DenseSearchService | None = None
sparse_service: SparseSearchService | None = None
reranker_service: RerankerService | None = None


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.api_title}


@app.get("/health/dense")
async def health_dense() -> dict:
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
    if sparse_service is None:
        raise HTTPException(
            status_code=503, detail="Sparse search service not initialized"
        )
    try:
        count = sparse_service.count()
    except SparseSearchError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ok", "db_path": settings.sparse_db_path, "row_count": count}


@app.get("/health/reranker")
async def health_reranker() -> dict:
    if reranker_service is None:
        raise HTTPException(
            status_code=503, detail="Reranker service not initialized"
        )
    try:
        reranker_service.self_check()
    except RerankError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ok", "model": settings.reranker_model_name}


@app.post("/api/v1/retrieve", response_model=list[ChunkResponse])
async def retrieve(request: RetrievalRequest) -> list[ChunkResponse]:
    if dense_service is None or sparse_service is None or reranker_service is None:
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

    candidates = fused[: settings.rerank_candidate_k]
    try:
        reranked = reranker_service.rerank(request.query, candidates)
    except RerankError as exc:
        raise HTTPException(status_code=503, detail=f"Reranking failed: {exc}") from exc

    return reranked[: request.top_k]


@app.on_event("startup")
async def on_startup() -> None:
    global dense_service, sparse_service, reranker_service
    logger.info(f"{settings.api_title} v{settings.api_version} starting up")
    dense_service = DenseSearchService()
    sparse_service = SparseSearchService()
    reranker_service = RerankerService()
