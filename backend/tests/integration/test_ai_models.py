from types import SimpleNamespace
from typing import get_args
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from src.iam.dependencies.identity import get_current_identity
from src.llm_router.dependencies import get_ai_model_repo
from src.llm_router.domain.dataclass import AIModel
from src.llm_router.domain.permissions.ai_models import CREATE, DELETE
from src.shared.application.dtos import Page
from src.shared.dependencies.database import DBSession


@pytest.mark.asyncio
async def test_get_models_returns_models(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    repository = AsyncMock()

    repository.find.return_value = Page.create(
        [
            {
                "name": "gpt-5-mini",
                "description": "Test model",
                "context": 128000,
            },
        ],
        total=1,
        page=1,
        size=50,
    )

    app.dependency_overrides[get_ai_model_repo] = lambda: repository
    app.dependency_overrides[get_current_identity] = lambda: SimpleNamespace()

    try:
        response = await client.post(
            "/api/v1/ai-models/search",
            json={
                "page": 1,
                "size": 50,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 1
    assert body["items"][0]["name"] == "gpt-5-mini"
    assert body["items"][0]["description"] == "Test model"
    assert body["items"][0]["context"] == 128000

    repository.find.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_model_creates_model_and_commits(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    repository = AsyncMock()
    session = AsyncMock()

    repository.create.return_value = AIModel(
        name="gpt-5-mini",
        description="Test model",
        context=128000,
    )

    app.dependency_overrides[get_current_identity] = lambda: SimpleNamespace(
        permissions={CREATE.code},
    )
    app.dependency_overrides[get_ai_model_repo] = lambda: repository

    db_dependency = get_args(DBSession)[1].dependency
    app.dependency_overrides[db_dependency] = lambda: session

    try:
        response = await client.post(
            "/api/v1/ai-models",
            json={
                "name": "gpt-5-mini",
                "description": "Test model",
                "context": 128000,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201

    body = response.json()

    assert body["name"] == "gpt-5-mini"
    assert body["description"] == "Test model"
    assert body["context"] == 128000

    repository.create.assert_awaited_once()
    session.commit.assert_awaited_once()

    model = repository.create.await_args.args[0]

    assert model.name == "gpt-5-mini"
    assert model.description == "Test model"
    assert model.context == 128000


@pytest.mark.asyncio
async def test_delete_model_deletes_model_and_commits(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    repository = AsyncMock()
    session = AsyncMock()
    uid = uuid4()

    app.dependency_overrides[get_current_identity] = lambda: SimpleNamespace(
        permissions={DELETE.code},
    )
    app.dependency_overrides[get_ai_model_repo] = lambda: repository

    db_dependency = get_args(DBSession)[1].dependency
    app.dependency_overrides[db_dependency] = lambda: session

    try:
        response = await client.delete(
            f"/api/v1/ai-models/{uid}",
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert response.content == b""

    repository.delete.assert_awaited_once_with(uid)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_model_returns_422_for_invalid_uuid(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    repository = AsyncMock()

    app.dependency_overrides[get_current_identity] = lambda: SimpleNamespace(
        permissions={DELETE.code},
    )
    app.dependency_overrides[get_ai_model_repo] = lambda: repository

    try:
        response = await client.delete(
            "/api/v1/ai-models/not-a-uuid",
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    repository.delete.assert_not_awaited()
