"""Centralized, type-safe application configuration.

Same pattern as fireguard-vector-store/src/config.py — one validated
Settings object, no magic strings/numbers scattered through the codebase.
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # API metadata
    api_title: str = Field(default="FireGuard Retrieval Agent")
    api_version: str = Field(default="0.1.0")
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["*"])

    # ChromaDB connection (dense search) — same values as the
    # fireguard-vector-store service this agent depends on
    chroma_host: str = Field(default="localhost")
    chroma_port: int = Field(default=8000)
    chroma_collection_name: str = Field(default="fire_safety_regulations")

    # Sparse index (SQLite FTS5) — path shared via volume with
    # fireguard-vector-store's data/ directory
    sparse_db_path: str = Field(default="data/bm25.db")

    # Embedding model — MUST match the model used to build the index in
    # fireguard-vector-store, or dense search returns nonsense results
    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2"
    )

    # Retrieval tuning
    dense_top_k: int = Field(default=20, gt=0)
    sparse_top_k: int = Field(default=20, gt=0)
    rrf_k: int = Field(default=60, gt=0)

    # Observability
    log_level: str = Field(default="INFO")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
