# fireguard-agent-retrieval

Hybrid (dense + sparse) retrieval API for the FireGuard RAG platform.
Queries `fireguard-vector-store`'s ChromaDB (dense/semantic) and SQLite
FTS5 (sparse/keyword) indexes, fuses results with Reciprocal Rank Fusion,
and optionally reranks with a cross-encoder.

## Build status

- [x] **Step 1** — FastAPI skeleton, config/logger/exceptions, `/health`,
      Dockerized + joined to `fireguard-vector-store`'s Docker network
- [x] **Step 2** — Dense search (ChromaDB), `/health/dense`
- [x] **Step 3** — Sparse search (SQLite FTS5, schema-corrected), `/health/sparse`
- [x] **Step 4** — RRF fusion + `/api/v1/retrieve`
- [ ] Step 5 — Reranker (optional)
- [ ] Step 6 — Dockerize + compose integration

## Step 1 — Run locally

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
cp .env.example .env

uvicorn app.main:app --reload --port 8001
```

Test it:

```bash
curl.exe http://localhost:8001/health
```

Expected:
```json
{"status":"ok","service":"FireGuard Retrieval Agent"}
```

Port `8001` (not `8000`) — that's already used by `fireguard-vector-store`'s
ChromaDB.

## Step 1 — Run with Docker (joins fireguard-vector-store's network)

**Prerequisite:** `fireguard-vector-store` must already be running (its
`chromadb` service and its `fireguard-net` Docker network need to exist).

**Folder layout assumed:** this repo sits next to `fireguard-vector-store`
as a sibling folder —

```
SLIT/
├── fireguard-vector-store/
└── fireguard-agent-retrieval/
```

If your layout differs, adjust the `volumes:` path in `docker-compose.yml`.

```powershell
Copy-Item .env.example .env
docker compose up -d --build
```

Test it:
```powershell
curl.exe http://localhost:8001/health
docker ps   # should show fireguard-agent-retrieval as (healthy)
```

If it fails with a "network not found" error, your `fireguard-vector-store`
folder isn't named exactly that — run `docker network ls`, find the actual
network name (it'll be `<your-folder-name>_fireguard-net`), and update the
`name:` field under `networks:` in `docker-compose.yml` to match.

## Step 2 — Dense search (ChromaDB)

`app/services/dense_search.py` loads the embedding model once at startup
(not per-request — that would add seconds of latency to every call) and
connects to `fireguard-vector-store`'s `fire_safety_regulations`
collection. It uses `get_collection` (not `get_or_create`), so it fails
loudly on startup if the collection doesn't exist yet, rather than
silently creating an empty one.

Rebuild and test:

```powershell
docker compose up -d --build
curl.exe http://localhost:8001/health/dense
```

Expected (chunk_count will match whatever's actually ingested):
```json
{"status":"ok","collection":"fire_safety_regulations","chunk_count":1094}
```

If `chunk_count` is `0` or the request returns `503`, `fireguard-vector
-store`'s ingestion hasn't run yet, or the collection name/host doesn't
match — check `docker compose logs agent-retrieval`.

## Step 3 — Sparse search (SQLite FTS5)

`app/services/sparse_search.py` queries the real `chunks_fts` schema
(`chunk_id`, `source`, `page`, `text`) — the original reference doc this
was built from queried columns (`id`, `metadata`, `rank`) that don't
exist in the actual table `fireguard-vector-store/src/sparse_index.py`
creates. Fixed to match. `id` values use the same `chunk_id` scheme as
dense search's ids, which matters for Step 4 — RRF fusion matches results
across both indexes by id, so this consistency is what lets it recognize
"the same chunk found both ways."

```powershell
docker compose up -d --build
curl.exe http://localhost:8001/health/sparse
```

Expected:
```json
{"status":"ok","db_path":"data/bm25.db","row_count":1094}
```

## Step 4 — Hybrid retrieval (`/api/v1/retrieve`)

Fetches top-20 from each retriever, fuses them with RRF (`app/services
/hybrid_fusion.py`), and returns the requested `top_k`. Each result's
`found_by` field shows whether dense, sparse, or **both** retrievers
surfaced that chunk — chunks found by both tend to rank highest, which
is the actual point of hybrid search.

**Fixed from the reference doc:** the `RetrievalRequest.tenant_id` field
was defined but never used anywhere — removed. Add it back only once
there's an actual multi-tenant collection scheme to route it to.

```powershell
docker compose up -d --build
```

```powershell
$body = @{ query = "What are the fire extinguisher requirements?"; top_k = 5 } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/retrieve" -Method Post -Body $body -ContentType "application/json"
```

Expected: a JSON array of up to 5 chunks, each with `id`, `text`,
`rrf_score`, `found_by`, `metadata`. Chunks with `"found_by":
["dense","sparse"]` near the top of the list confirm fusion is actually
combining both retrievers, not just picking one.
