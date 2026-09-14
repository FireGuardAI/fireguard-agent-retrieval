from app.config import settings


def reciprocal_rank_fusion(
    dense_results: list[dict],
    sparse_results: list[dict],
    k: int | None = None,
) -> list[dict]:
    k = k if k is not None else settings.rrf_k
    rrf_scores: dict[str, float] = {}
    doc_map: dict[str, dict] = {}
    found_by: dict[str, set[str]] = {}

    def add_ranks(results: list[dict], label: str) -> None:
        for rank, doc in enumerate(results, start=1):
            doc_id = doc["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            doc_map.setdefault(doc_id, doc)
            found_by.setdefault(doc_id, set()).add(label)

    add_ranks(dense_results, "dense")
    add_ranks(sparse_results, "sparse")

    fused = []
    for doc_id, score in sorted(
        rrf_scores.items(), key=lambda item: item[1], reverse=True
    ):
        doc = doc_map[doc_id]
        fused.append(
            {
                "id": doc_id,
                "text": doc["text"],
                "metadata": doc.get("metadata"),
                "rrf_score": score,
                "found_by": sorted(found_by[doc_id]),
            }
        )
    return fused
