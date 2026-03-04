# syntax = docker/dockerfile:1.9-labs    # ← обязательно для --mount=type=cache,link

# ────────────────────────────────────────────────
# Стадия 1 — сборка зависимостей (builder)
# ────────────────────────────────────────────────
FROM python:3.13-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    HF_HOME=/app/hf_cache

WORKDIR /app

# Копируем только lock-файлы / requirements (самое важное!)
COPY pyproject.toml uv.lock requirements.txt* ./

# Устанавливаем uv (самый быстрый installer в 2026)
RUN --mount=type=cache,target=/root/.cache/uv \
    pip install --no-cache-dir uv && \
    uv sync --frozen --no-install-project --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# ------------------- ЗАГРУЗКА МОДЕЛИ -------------------
# Теперь, когда зависимости установлены, скачиваем модель эмбеддингов
# (эта команда сохранит файлы в $HF_HOME)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('deepvk/USER-bge-m3')"
# -------------------------------------------------------

# ────────────────────────────────────────────────
# Стадия 2 — финальный образ (runtime)
# ────────────────────────────────────────────────
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/hf_cache

WORKDIR /app

# Копируем виртуальное окружение из builder
COPY --from=builder /app/.venv /app/.venv

# Копируем папку с загруженной моделью
COPY --from=builder /app/hf_cache /app/hf_cache

# Добавляем venv в PATH
ENV PATH="/app/.venv/bin:$PATH"

# Копируем весь код (самое последнее!)
COPY . .

# Если используете fastapi/uvicorn/gunicorn и т.п.
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# или
CMD ["python", "main.py"]