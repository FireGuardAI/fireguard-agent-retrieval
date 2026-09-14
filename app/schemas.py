from pydantic import BaseModel, Field


class RetrievalRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The search query text")
    top_k: int = Field(default=5, gt=0, le=50)


class ChunkResponse(BaseModel):
    id: str
    text: str
    rrf_score: float
    rerank_score: float
    found_by: list[str]
    metadata: dict | None = None
