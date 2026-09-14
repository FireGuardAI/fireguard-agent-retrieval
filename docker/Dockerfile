# syntax=docker/dockerfile:1.7
# ^ MUST be the very first line — enables the BuildKit cache-mount below

FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .

# --mount=type=cache persists pip's download cache across rebuilds —
# same reasoning as fireguard-vector-store/docker/Dockerfile.ingest
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user -r requirements.txt

FROM python:3.12-slim
WORKDIR /app

# Non-root user — never run production containers as root
RUN groupadd -r fireguard && useradd -r -g fireguard fireguard

COPY --from=builder /root/.local /home/fireguard/.local
COPY app/ ./app/

ENV PATH=/home/fireguard/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/.cache/huggingface

# .cache dir pre-created + chowned for the same reason as the ingest
# service: Step 2 adds an embedding model download that needs a
# writable HOME-relative cache dir for the non-root user
RUN mkdir -p /app/.cache/huggingface && chown -R fireguard:fireguard /app
USER fireguard

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
