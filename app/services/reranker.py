from sentence_transformers import CrossEncoder

from app.config import settings
from app.exceptions import RerankError
from app.logger import get_logger

logger = get_logger(__name__)


class RerankerService:
    def __init__(self):
        logger.info(f"Loading reranker model: {settings.reranker_model_name}")
        self._model = CrossEncoder(settings.reranker_model_name)
        logger.info("RerankerService ready")

    def self_check(self) -> None:
        try:
            self._model.predict([("test query", "test passage")])
        except Exception as exc:
            raise RerankError(str(exc)) from exc

    def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        if not candidates:
            return []
        try:
            pairs = [(query, c["text"]) for c in candidates]
            scores = self._model.predict(pairs)
        except Exception as exc:
            raise RerankError(str(exc)) from exc

        reranked = [
            {**candidate, "rerank_score": float(score)}
            for candidate, score in zip(candidates, scores)
        ]
        reranked.sort(key=lambda c: c["rerank_score"], reverse=True)
        return reranked
