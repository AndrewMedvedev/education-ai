import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from qdrant_client import models

from .logging import configure_logging
from .others import thread_executor
from .qdrant import qdrant_client
from .rabbit import router as rabbit_router
from .redis import checkpointer, redis_client

_BOOTSTRAP_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("alembic", "upgrade", "head"),
    ("src.cli", "create-permissions"),
    ("src.cli", "create-first-admin"),
    ("src.cli", "create-super-admin"),
    ("src.cli", "create-default-organization"),
    # ("src.cli", "init-s3-buckets"),
)


async def _run_bootstrap_commands() -> None:
    """Запускает команды необходимые для старта приложения."""

    from src.shared.utils.cli import run_cli_command  # ruff: ignore[import-outside-top-level]

    for cmd in _BOOTSTRAP_COMMANDS:
        full_cmd = (sys.executable, "-m", *cmd)
        await run_cli_command(*full_cmd)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(log_level="INFO")

    await redis_client.ping()  # pyright: ignore[reportGeneralTypeIssues]

    await _run_bootstrap_commands()
    await checkpointer.setup()
    exists = await qdrant_client.collection_exists("MAIN_COLLECTION")
    if not exists:
        await qdrant_client.create_collection(
            collection_name="MAIN_COLLECTION",
            vectors_config={
                "dense": models.VectorParams(
                    size=1024,
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={"bm25": models.SparseVectorParams()},
        )
    async with rabbit_router.lifespan_context(app):
        yield
    thread_executor.shutdown(wait=True)


__all__ = ["lifespan"]
