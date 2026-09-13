# syntax = docker/dockerfile:1.9-labs    # ← обязательно для --mount=type=cache,link

# ────────────────────────────────────────────────
# Стадия 1 — сборка зависимостей (builder)
# ────────────────────────────────────────────────
FROM python:3.13-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Копируем только lock-файлы / requirements (самое важное!)
COPY pyproject.toml uv.lock requirements.txt* ./

# Устанавливаем uv (самый быстрый installer в 2026)
RUN --mount=type=cache,target=/root/.cache/uv \
    pip install --no-cache-dir uv && \
    uv sync --frozen --no-install-project --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# ────────────────────────────────────────────────
# Стадия 2 — финальный образ (runtime)
# ────────────────────────────────────────────────
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Копируем виртуальное окружение из builder
COPY --from=builder /app/.venv /app/.venv


ENV PATH="/app/.venv/bin:$PATH"

COPY . .

CMD ["python", "main.py"]
