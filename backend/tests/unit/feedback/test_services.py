from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from src.feedback.application.dtos import FeedbackFilters
from src.feedback.application.services import FeedbackService
from src.feedback.domain.entities import Feedback
from src.feedback.domain.events import FeedbackCreated
from src.iam.domain.vo import Email
from src.shared.application.dtos import Page, Pagination
from src.shared.application.transaction import Transaction
from src.shared.domain.exceptions import RateLimitExceededError
from src.shared.utils.time import current_datetime


@pytest.fixture
def repository() -> AsyncMock:
    repo = AsyncMock()
    repo.find.return_value = Page.create([], total=0, page=1, size=1)
    return repo


@pytest.fixture
def transaction() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(repository: AsyncMock, transaction: AsyncMock) -> FeedbackService:
    return FeedbackService(feedback_repo=repository, transaction=transaction)


@pytest.mark.asyncio
@pytest.mark.parametrize("recent_count", [0, 4])
async def test_create_checks_limit_saves_and_commits(
    service: FeedbackService,
    repository: AsyncMock,
    transaction: AsyncMock,
    user_id: UUID,
    recent_count: int,
) -> None:
    repository.find.return_value = Page.create([], total=recent_count, page=1, size=1)
    before = current_datetime() - timedelta(days=1)

    feedback = await service.create_feedback(
        user_id=user_id,
        email=Email("user@example.com"),
        rating=4,
        comment="  Спасибо  ",
    )

    after = current_datetime() - timedelta(days=1)
    assert isinstance(feedback, Feedback)
    assert feedback.user_id == user_id
    assert feedback.email == Email("user@example.com")
    assert feedback.rating.value == 4
    assert feedback.comment == "Спасибо"
    pagination, filters = repository.find.await_args.args
    assert pagination == Pagination(page=1, size=1)
    assert repository.find.await_args.kwargs == {"user_id": user_id}
    assert before <= filters.created_after <= after
    repository.create.assert_awaited_once_with(feedback)
    transaction.assert_awaited_once_with(feedback)


@pytest.mark.asyncio
@pytest.mark.parametrize("recent_count", [5, 6])
async def test_daily_limit_returns_429_without_saving(
    service: FeedbackService,
    repository: AsyncMock,
    transaction: AsyncMock,
    user_id: UUID,
    recent_count: int,
) -> None:
    repository.find.return_value = Page.create([], total=recent_count, page=1, size=1)

    with pytest.raises(RateLimitExceededError) as exc_info:
        await service.create_feedback(
            user_id=user_id,
            email=Email("user@example.com"),
            rating=5,
            comment="Повторный отзыв",
        )

    assert exc_info.value.status_code == 429
    repository.find.assert_awaited_once()
    repository.create.assert_not_awaited()
    transaction.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_comment_does_not_save(
    service: FeedbackService,
    repository: AsyncMock,
    transaction: AsyncMock,
    user_id: UUID,
) -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        await service.create_feedback(
            user_id=user_id,
            email=Email("user@example.com"),
            rating=5,
            comment="   ",
        )

    repository.create.assert_not_awaited()
    transaction.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_commits_and_publishes_registered_event(
    repository: AsyncMock, user_id: UUID
) -> None:
    uow = AsyncMock()
    publisher = AsyncMock()
    service = FeedbackService(repository, Transaction(uow, publisher))

    feedback = await service.create_feedback(
        user_id=user_id,
        email=Email("user@example.com"),
        rating=5,
        comment="Спасибо",
    )

    uow.commit.assert_awaited_once()
    publisher.publish_all.assert_awaited_once()
    events = publisher.publish_all.await_args.args[0]
    assert len(events) == 1
    assert isinstance(events[0], FeedbackCreated)
    assert events[0].feedback_id == feedback.id

