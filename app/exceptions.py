"""Custom exceptions — never let raw library errors leak into API responses."""


class RetrievalError(Exception):
    """Base exception for the retrieval agent domain."""


class DenseSearchError(RetrievalError):
    """Raised when the ChromaDB dense search fails."""


class SparseSearchError(RetrievalError):
    """Raised when the SQLite FTS5 sparse search fails."""


class RerankError(RetrievalError):
    """Raised when cross-encoder reranking fails."""
