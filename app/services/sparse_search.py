"""Sparse (keyword/BM25) search against fireguard-vector-store's SQLite
FTS5 inverted index.

Schema note: the pasted reference implementation this was built from
queried columns `id`, `metadata`, `rank` — none of which exist in the
real `chunks_fts` table. The actual schema (see
fireguard-vector-store/src/sparse_index.py) is:
    chunks_fts(chunk_id UNINDEXED, source UNINDEXED, page UNINDEXED, text)
This implementation queries the real columns and reconstructs a
`metadata` dict from `source`/`page`, matching the shape dense_search.py
returns so both feed cleanly into the same RRF fusion step (Step 4).
"""
import sqlite3
from pathlib import Path

from app.config import settings
from app.exceptions import SparseSearchError
from app.logger import get_logger

logger = get_logger(__name__)


class SparseSearchService:
    def __init__(self, db_path: str | None = None):
        self._db_path = Path(db_path or settings.sparse_db_path)
        if not self._db_path.exists():
            raise SparseSearchError(
                f"Sparse index not found at {self._db_path} — has "
                f"fireguard-vector-store's ingestion run yet?"
            )
        logger.info(f"SparseSearchService ready ({self._db_path})")

    def count(self) -> int:
        """Used by /health/sparse to prove the index actually has rows,
        not just that the .db file exists."""
        try:
            conn = sqlite3.connect(self._db_path)
            try:
                return conn.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0]
            finally:
                conn.close()
        except Exception as exc:
            raise SparseSearchError(str(exc)) from exc

    @staticmethod
    def _build_match_query(query: str) -> str:
        # OR-join terms so a multi-word query returns candidates matching
        # ANY keyword (wide recall) rather than requiring every word to
        # match — RRF fusion (Step 4) is what narrows results down, not
        # this query itself. Non-alphanumeric tokens are dropped since
        # FTS5's MATCH syntax treats punctuation as query syntax.
        terms = [w for w in query.split() if w.isalnum()]
        if not terms:
            return ""
        return " OR ".join(f'"{t}"' for t in terms)

    def search(self, query: str, top_k: int = 20) -> list[dict]:
        match_query = self._build_match_query(query)
        if not match_query:
            return []

        try:
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.execute(
                    """
                    SELECT chunk_id, source, page, text, bm25(chunks_fts) AS score
                    FROM chunks_fts
                    WHERE chunks_fts MATCH ?
                    ORDER BY score
                    LIMIT ?
                    """,
                    (match_query, top_k),
                )
                rows = cursor.fetchall()
            finally:
                conn.close()
        except Exception as exc:
            raise SparseSearchError(str(exc)) from exc

        return [
            {
                "id": chunk_id,  # same chunk_id scheme as dense_search.py's
                                  # ids — required so RRF can match the SAME
                                  # chunk found by both dense and sparse
                "text": text,
                "metadata": {"source": source, "page": page},
                "score": score,
                "source": "sparse",
            }
            for chunk_id, source, page, text, score in rows
        ]
