# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user -r requirements.txt

FROM python:3.12-slim
WORKDIR /app

RUN groupadd -r fireguard && useradd -r -g fireguard fireguard

COPY --from=builder /root/.local /home/fireguard/.local
COPY app/ ./app/

ENV PATH=/home/fireguard/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/.cache/huggingface

RUN mkdir -p /app/.cache/huggingface && chown -R fireguard:fireguard /app
USER fireguard

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
