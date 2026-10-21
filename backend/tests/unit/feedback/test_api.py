from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI

from src.feedback.api.v1.feedback import create_feedback, get_feedbacks, router
from src.feedback.application.dtos import FeedbackCreate, FeedbackFilters
from src.feedback.domain.entities import Feedback
from src.iam.application.dtos import Identity, IdentityType
from src.iam.domain.vo import Email
from src.shared.application.dtos import Page, Pagination


@pytest.mark.asyncio
async def test_post_uses_identity_not_client_fields(
    feedback: Feedback, user_id: UUID
) -> None:
    identity = Identity(
        organization_id=uuid4(),
        id=user_id,
        type=IdentityType.USER,
        email=Email("user@example.com"),
    )
    service = AsyncMock()
    service.create_feedback.return_value = feedback
    data = FeedbackCreate(rating=5, comment="Хорошая платформа")

    response = await create_feedback(data=data, identity=identity, service=service)

    service.create_feedback.assert_awaited_once_with(
        user_id=user_id,
        email=Email("user@example.com"),
        rating=5,
        comment="Хорошая платформа",
    )
    assert response.id == feedback.id
    assert response.user_id == user_id
    assert response.comment == feedback.comment


@pytest.mark.asyncio
async def test_get_passes_filters_and_pagination(feedback: Feedback) -> None:
    pagination = Pagination(page=2, size=3)
    filters = FeedbackFilters(rating=5, sort="created_at:asc")
    repo = AsyncMock()
    repo.find.return_value = Page.create([feedback], total=4, page=2, size=3)

    response = await get_feedbacks(
        repo=repo,
        pagination=pagination,
        filters=filters,
    )

    repo.find.assert_awaited_once_with(pagination, filters)
    assert response.total == 4
    assert response.page == 2
    assert response.items[0].id == feedback.id


def test_routes_expose_one_post_and_one_get_with_required_schema() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    spec = app.openapi()
    path = spec["paths"]["/api/v1/feedbacks"]

    assert set(path) == {"post", "get"}
    assert path["post"]["responses"]["201"]
    assert "rating" in spec["components"]["schemas"]["FeedbackCreate"]["required"]
    assert "comment" in spec["components"]["schemas"]["FeedbackCreate"]["required"]
    assert any(
        parameter["name"] == "filters" and parameter["in"] == "query"
        for parameter in path["get"]["parameters"]
    )
