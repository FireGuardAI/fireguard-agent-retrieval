from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # API metadata
    api_title: str = Field(default="FireGuard Retrieval Agent")
    api_version: str = Field(default="0.1.0")
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["*"])

    chroma_host: str = Field(default="localhost")
    chroma_port: int = Field(default=8000)
    chroma_collection_name: str = Field(default="fire_safety_regulations")

    sparse_db_path: str = Field(default="data/bm25.db")

    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2"
    )

    dense_top_k: int = Field(default=20, gt=0)
    sparse_top_k: int = Field(default=20, gt=0)
    rrf_k: int = Field(default=60, gt=0)

    reranker_model_name: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    rerank_candidate_k: int = Field(default=20, gt=0)

    log_level: str = Field(default="INFO")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
