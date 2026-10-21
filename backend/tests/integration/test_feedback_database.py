"""Проверки feedback на локальной PostgreSQL без сохранения тестовых отзывов."""

import os
from collections.abc import AsyncIterator
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from src.core.database import get_db, postgres_config
from src.feedback.api.v1.feedback import router as feedback_router
from src.feedback.application.dtos import FeedbackFilters
from src.feedback.application.services import FeedbackService
from src.feedback.domain.entities import Feedback
from src.feedback.infra.database.models import FeedbackOrm
from src.feedback.infra.database.repos.feedback import SqlFeedbackRepository
from src.feedback.domain.permissions.feedback import READ
from src.iam.application.dtos import Identity, IdentityType
from src.iam.dependencies.identity import get_current_identity
from src.iam.domain.vo import Email
from src.shared.application.dtos import Pagination
from src.shared.application.transaction import Transaction
from src.shared.dependencies.events import get_event_publisher
from src.shared.domain.exceptions import RateLimitExceededError
from src.shared.utils.time import current_datetime


@pytest_asyncio.fixture
async def feedback_engine() -> AsyncIterator[AsyncEngine]:
    if os.getenv("RUN_FEEDBACK_DB_TESTS") != "1":
        pytest.skip("Установите RUN_FEEDBACK_DB_TESTS=1 для тестов с PostgreSQL")
    if postgres_config.host not in {"localhost", "127.0.0.1"}:
        pytest.fail("Интеграционные тесты feedback разрешены только на локальной PostgreSQL")

    engine = create_async_engine(postgres_config.uri, hide_parameters=True)
    try:
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT to_regclass('public.feedbacks')")) == "feedbacks"
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def feedback_session(feedback_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with feedback_engine.connect() as connection:
        outer = await connection.begin()
        try:
            async with AsyncSession(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            ) as session:
                yield session
        finally:
            await outer.rollback()


@pytest.mark.asyncio
async def test_create_persists_feedback_and_enforces_daily_limit(
    feedback_session: AsyncSession,
) -> None:
    repository = SqlFeedbackRepository(feedback_session)
    publisher = AsyncMock()
    service = FeedbackService(repository, Transaction(feedback_session, publisher))
    user_id = uuid4()

    feedbacks = [
        await service.create_feedback(
            user_id=user_id,
            email=Email("test@example.com"),
            rating=5,
            comment=f"  Отзыв {index}  ",
        )
        for index in range(5)
    ]

    stored = await feedback_session.get(FeedbackOrm, feedbacks[-1].id)
    assert stored is not None
    assert stored.user_id == user_id
    assert stored.rating == 5
    assert stored.comment == "Отзыв 4"
    recent = await repository.find(
        Pagination(page=1, size=1),
        FeedbackFilters(created_after=current_datetime() - timedelta(days=1)),
        user_id=user_id,
    )
    assert recent.total == 5
    assert publisher.publish_all.await_count == 5

    with pytest.raises(RateLimitExceededError):
        await service.create_feedback(
            user_id=user_id,
            email=Email("test@example.com"),
            rating=4,
            comment="Повторный отзыв",
        )


@pytest.mark.asyncio
async def test_feedback_http_round_trip_uses_postgres(feedback_session: AsyncSession) -> None:
    user_id = uuid4()
    publisher = AsyncMock()
    identity = Identity(
        organization_id=uuid4(),
        id=user_id,
        type=IdentityType.USER,
        email=Email("test@example.com"),
        permissions=frozenset({READ.code}),
    )
    app = FastAPI()
    app.include_router(feedback_router, prefix="/api/v1")
    app.dependency_overrides[get_current_identity] = lambda: identity
    app.dependency_overrides[get_db] = lambda: feedback_session
    app.dependency_overrides[get_event_publisher] = lambda: publisher

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/v1/feedbacks",
            json={"rating": 4, "comment": "  Всё понятно  "},
        )
        listed = await client.get("/api/v1/feedbacks?rating=4&sort=created_at:desc")

    assert created.status_code == 201
    assert created.json()["user_id"] == str(user_id)
    assert created.json()["comment"] == "Всё понятно"
    assert created.json()["rating"] == {"value": 4}
    assert "_events" not in created.json()
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [created.json()["id"]]
    assert "_events" not in listed.json()["items"][0]
    publisher.publish_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_feedback_filter_sort_and_pagination(feedback_session: AsyncSession) -> None:
    repository = SqlFeedbackRepository(feedback_session)
    now = current_datetime()
    feedbacks = [
        Feedback.create(
            user_id=uuid4(),
            email=Email("test@example.com"),
            rating=rating,
            comment=comment,
        )
        for rating, comment in [(4, "Ранний"), (5, "Другая оценка"), (4, "Поздний")]
    ]
    for index, feedback in enumerate(feedbacks):
        feedback.created_at = now + timedelta(seconds=index)
        await repository.create(feedback)
    await feedback_session.flush()

    ascending = await repository.find(
        Pagination(page=1, size=1), FeedbackFilters(rating=4, sort="created_at:asc")
    )
    descending = await repository.find(
        Pagination(page=1, size=1), FeedbackFilters(rating=4, sort="created_at:desc")
    )
    second_page = await repository.find(
        Pagination(page=2, size=1), FeedbackFilters(rating=4, sort="created_at:asc")
    )

    assert ascending.total == descending.total == second_page.total == 2
    assert [item.comment for item in ascending.items] == ["Ранний"]
    assert [item.comment for item in descending.items] == ["Поздний"]
    assert [item.comment for item in second_page.items] == ["Поздний"]
