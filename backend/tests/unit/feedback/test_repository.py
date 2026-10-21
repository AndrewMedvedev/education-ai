from typing import Literal

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.dialects import postgresql

from src.feedback.application.dtos import FeedbackFilters
from src.feedback.domain.entities import Feedback
from src.feedback.infra.database.models import FeedbackOrm
from src.feedback.infra.database.repos import feedback as repository_module
from src.feedback.infra.database.repos.feedback import SqlFeedbackRepository
from src.shared.application.dtos import Page, Pagination


@pytest.mark.asyncio
async def test_create_uses_existing_mapper_and_session(
    mock_session: AsyncMock, feedback: Feedback
) -> None:
    repository = SqlFeedbackRepository(mock_session)

    result = await repository.create(feedback)

    mock_session.add.assert_called_once()
    model = mock_session.add.call_args.args[0]
    assert isinstance(model, FeedbackOrm)
    assert model.user_id == feedback.user_id
    assert model.email == feedback.email.value
    assert model.rating == feedback.rating.value
    assert model.comment == feedback.comment
    assert result.id == feedback.id
    assert result.comment == feedback.comment


@pytest.mark.asyncio
@pytest.mark.parametrize("rating", [None, 4])
@pytest.mark.parametrize("order", ["asc", "desc"])
async def test_find_filters_active_feedbacks_and_sorts_by_date(
    mock_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    rating: int | None,
    order: Literal["asc", "desc"],
) -> None:
    pagination = Pagination(page=2, size=3)
    expected = Page.create([], total=0, page=2, size=3)
    paginate = AsyncMock(return_value=expected)
    monkeypatch.setattr(repository_module, "paginate", paginate)
    repository = SqlFeedbackRepository(mock_session)

    filters = FeedbackFilters(rating=rating, sort=f"created_at:{order}")
    result = await repository.find(pagination, filters)

    assert result is expected
    paginate.assert_awaited_once()
    kwargs = paginate.await_args.kwargs
    assert kwargs["session"] is mock_session
    assert kwargs["model"] is FeedbackOrm
    assert kwargs["pagination"] is pagination
    assert kwargs["sort"] == f"created_at:{order}"
    compiled = kwargs["stmt"].compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "feedbacks.deleted_at IS NULL" in sql
    assert "feedbacks.user_id =" not in sql
    if rating is None:
        assert "feedbacks.rating =" not in sql
    else:
        assert "feedbacks.rating =" in sql
        assert rating in compiled.params.values()


@pytest.mark.asyncio
async def test_find_filters_by_internal_user_id(
    mock_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    user_id: UUID,
) -> None:
    paginate = AsyncMock(return_value=Page.create([], total=0, page=1, size=1))
    monkeypatch.setattr(repository_module, "paginate", paginate)
    repository = SqlFeedbackRepository(mock_session)

    await repository.find(Pagination(page=1, size=1), FeedbackFilters(), user_id=user_id)

    statement = paginate.await_args.kwargs["stmt"]
    compiled = statement.compile(dialect=postgresql.dialect())
    assert "feedbacks.user_id =" in str(compiled)
    assert user_id in compiled.params.values()


@pytest.mark.asyncio
@pytest.mark.parametrize("order", ["asc", "desc"])
async def test_find_orders_sql_before_pagination(
    mock_session: AsyncMock, order: Literal["asc", "desc"]
) -> None:
    mock_session.scalar.return_value = 1
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = result
    repository = SqlFeedbackRepository(mock_session)

    await repository.find(
        Pagination(page=2, size=3),
        FeedbackFilters(sort=f"created_at:{order}"),
    )

    statement = mock_session.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert f"ORDER BY feedbacks.created_at {order.upper()}" in sql
    assert "LIMIT" in sql and "OFFSET" in sql


def test_feedback_table_has_rating_check_and_user_date_index() -> None:
    table = FeedbackOrm.__table__

    assert {column.name for column in table.columns} >= {
        "id", "user_id", "email", "rating", "comment", "created_at",
    }
    assert "ix_feedbacks_user_created_at" in {index.name for index in table.indexes}
    assert "ck_feedbacks_rating_range" in {constraint.name for constraint in table.constraints}
