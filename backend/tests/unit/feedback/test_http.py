from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.feedback.api.v1.feedback import router
from src.feedback.domain.permissions.feedback import READ
from src.iam.application.dtos import Identity, IdentityType
from src.iam.dependencies.identity import get_current_identity
from src.iam.domain.vo import Email
from src.shared.dependencies.events import get_event_publisher
from src.shared.domain.exceptions import DomainError


def _client(identity: Identity) -> tuple[TestClient, AsyncMock, AsyncMock]:
    """Поднимает только feedback API с подменёнными внешними зависимостями."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = 0
    publisher = AsyncMock()
    app.dependency_overrides[get_current_identity] = lambda: identity
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_event_publisher] = lambda: publisher

    @app.exception_handler(DomainError)
    def handle_app_error(_request: Request, error: DomainError) -> JSONResponse:
        return JSONResponse(status_code=error.status_code, content={"error": error.error_code})

    return TestClient(app), session, publisher


def test_http_post_creates_feedback_using_token_identity() -> None:
    user_id = uuid4()
    identity = Identity(
        organization_id=uuid4(),
        id=user_id,
        type=IdentityType.USER,
        email=Email("user@example.com"),
    )
    client, session, publisher = _client(identity)

    response = client.post(
        "/api/v1/feedbacks",
        json={"rating": 5, "comment": "  Отлично  "},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == str(user_id)
    assert body["email"] == {"value": "user@example.com"}
    assert body["rating"] == {"value": 5}
    assert body["comment"] == "Отлично"
    session.execute.assert_not_awaited()
    session.scalar.assert_awaited_once()
    session.add.assert_called_once()
    session.commit.assert_awaited_once()
    publisher.publish_all.assert_awaited_once()


def test_http_post_rejects_client_supplied_identity() -> None:
    identity = Identity(
        organization_id=uuid4(),
        id=uuid4(),
        type=IdentityType.USER,
        email=Email("user@example.com"),
    )
    client, session, _publisher = _client(identity)

    response = client.post(
        "/api/v1/feedbacks",
        json={"rating": 5, "comment": "Отзыв", "user_id": str(uuid4())},
    )

    assert response.status_code == 422
    session.add.assert_not_called()


def test_http_get_allows_service_account_with_permission_and_applies_filters() -> None:
    identity = Identity(
        organization_id=uuid4(),
        id=uuid4(),
        type=IdentityType.SERVICE_ACCOUNT,
        permissions=frozenset({READ.code}),
    )
    client, session, _publisher = _client(identity)

    response = client.get("/api/v1/feedbacks?page=2&size=3&rating=4&sort=created_at:asc")

    assert response.status_code == 200
    assert response.json()["page"] == 2
    assert response.json()["size"] == 3
    assert response.json()["items"] == []
    session.scalar.assert_awaited_once()
    statement = session.scalar.await_args.args[0]
    assert 4 in statement.compile().params.values()


def test_http_get_rejects_unknown_sort_order() -> None:
    identity = Identity(
        organization_id=uuid4(),
        id=uuid4(),
        type=IdentityType.USER,
        email=Email("admin@example.com"),
        permissions=frozenset({READ.code}),
    )
    client, session, _publisher = _client(identity)

    response = client.get("/api/v1/feedbacks?sort=created_at:random")

    assert response.status_code == 422
    session.scalar.assert_not_awaited()


def test_http_get_denies_identity_without_permission() -> None:
    identity = Identity(
        organization_id=uuid4(),
        id=uuid4(),
        type=IdentityType.USER,
        email=Email("user@example.com"),
        roles=frozenset({"user"}),
    )
    client, session, _publisher = _client(identity)

    response = client.get("/api/v1/feedbacks")

    assert response.status_code == 403
    session.scalar.assert_not_awaited()


@pytest.mark.parametrize("rating", [0, 6])
def test_http_get_rejects_invalid_rating(rating: int) -> None:
    identity = Identity(
        organization_id=uuid4(),
        id=uuid4(),
        type=IdentityType.USER,
        email=Email("admin@example.com"),
        permissions=frozenset({READ.code}),
    )
    client, session, _publisher = _client(identity)

    response = client.get(f"/api/v1/feedbacks?rating={rating}")

    assert response.status_code == 422
    session.scalar.assert_not_awaited()
