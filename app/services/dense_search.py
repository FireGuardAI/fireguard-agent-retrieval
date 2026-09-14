import chromadb
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.exceptions import DenseSearchError
from app.logger import get_logger

logger = get_logger(__name__)


class DenseSearchService:
    def __init__(self):
        logger.info(f"Loading embedding model: {settings.embedding_model_name}")
        self._model = SentenceTransformer(settings.embedding_model_name)

        try:
            self._client = chromadb.HttpClient(
                host=settings.chroma_host, port=settings.chroma_port
            )
            self._collection = self._client.get_collection(
                name=settings.chroma_collection_name
            )
        except Exception as exc:
            raise DenseSearchError(
                f"Could not reach ChromaDB collection "
                f"'{settings.chroma_collection_name}' at "
                f"{settings.chroma_host}:{settings.chroma_port}: {exc}"
            ) from exc

        logger.info("DenseSearchService ready")

    def count(self) -> int:
        try:
            return self._collection.count()
        except Exception as exc:
            raise DenseSearchError(str(exc)) from exc

    def search(self, query: str, top_k: int = 20) -> list[dict]:
        try:
            query_embedding = self._model.encode([query]).tolist()[0]
            results = self._collection.query(
                query_embeddings=[query_embedding], n_results=top_k
            )
        except Exception as exc:
            raise DenseSearchError(str(exc)) from exc

        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        return [
            {
                "id": doc_id,
                "text": text,
                "metadata": meta,
                "distance": dist,
                "source": "dense",
            }
            for doc_id, text, meta, dist in zip(
                ids, documents, metadatas, distances
            )
        ]
