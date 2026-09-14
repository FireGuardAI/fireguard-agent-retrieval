"""Pydantic request/response models for the retrieval API.

Note: the reference doc this project started from had a `tenant_id`
field on RetrievalRequest that was never used anywhere in the request
handler — dead code. It's left out here; add it back only once there's
an actual multi-tenant collection scheme to route to.
"""
from pydantic import BaseModel, Field


class RetrievalRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The search query text")
    top_k: int = Field(default=5, gt=0, le=50)


class ChunkResponse(BaseModel):
    id: str
    text: str
    rrf_score: float
    found_by: list[str]
    metadata: dict | None = None
