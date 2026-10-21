from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.redis import RedisContainer

import src.courses.infra.database.models  # noqa: F401
from src.core.database import Base
from src.llm_router.api.v1 import router as llm_router
from src.llm_router.api.v1.ai_models import router as ai_models_router


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(llm_router, prefix="/api/v1")
    app.include_router(ai_models_router, prefix="/api/v1")
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture(scope="session")
def postgres_container():
    """Поднимает PostgreSQL для интеграционных тестов."""
    with PostgresContainer(image="postgres:16.9", driver="asyncpg") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def redis_container():
    """Поднимает Redis для интеграционных тестов."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest_asyncio.fixture
async def redis_client(redis_container):
    """Возвращает очищенный Redis-клиент для одного теста."""
    client = Redis(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(6379)),
    )
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


@pytest_asyncio.fixture
async def engine(postgres_container):
    """Создаёт схему приложения в тестовой базе данных."""
    engine = create_async_engine(postgres_container.get_connection_url())
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncIterator[AsyncSession]:
    """Возвращает изолированную асинхронную сессию тестовой базы данных."""
    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sessionmaker() as session:
        yield session
        await session.rollback()
