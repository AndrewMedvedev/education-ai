from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from src.iam.dependencies.identity import get_current_identity
from src.llm_router.dependencies import (
    get_llm_image_router,
    get_llm_text_router,
)
from src.llm_service import (
    LLMImageResponse,
    LLMTextResponse,
)


@pytest.mark.asyncio
async def test_invoke_text_returns_service_response(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = AsyncMock()
    service.call_llm.return_value = LLMTextResponse(
        raw_text="Ответ",
        total_tokens=5,
    )

    app.dependency_overrides[get_llm_text_router] = lambda: service
    app.dependency_overrides[get_current_identity] = lambda: object()

    try:
        response = await client.post(
            "/api/v1/responses/text",
            json={
                "input": [{"content": "Проверка"}],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    body = response.json()

    assert body["raw_text"] == "Ответ"
    assert body["total_tokens"] == 5

    service.call_llm.assert_awaited_once()

    call = service.call_llm.await_args
    assert call.kwargs["model"] is None
    assert call.kwargs["schema"].messages == [
        {"content": "Проверка"},
    ]


@pytest.mark.asyncio
async def test_invoke_image_returns_service_response(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = AsyncMock()
    service.call_llm.return_value = LLMImageResponse(
        size="1024x1024",
        image="base64-image",
        total_tokens=5,
    )

    app.dependency_overrides[get_llm_image_router] = lambda: service
    app.dependency_overrides[get_current_identity] = lambda: object()

    try:
        response = await client.post(
            "/api/v1/responses/image",
            json={
                "prompt": "Нарисуй схему",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    body = response.json()

    assert body["size"] == "1024x1024"
    assert body["image"] == "base64-image"
    assert body["total_tokens"] == 5

    service.call_llm.assert_awaited_once()

    call = service.call_llm.await_args
    assert call.kwargs["model"] is None
    assert call.kwargs["schema"].messages == "Нарисуй схему"


@pytest.mark.asyncio
async def test_invoke_text_returns_422_for_invalid_body(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = AsyncMock()

    app.dependency_overrides[get_llm_text_router] = lambda: service
    app.dependency_overrides[get_current_identity] = lambda: object()

    try:
        response = await client.post(
            "/api/v1/responses/text",
            json={
                "input": "Проверка",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    service.call_llm.assert_not_awaited()


@pytest.mark.asyncio
async def test_invoke_image_returns_422_for_invalid_body(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    service = AsyncMock()

    app.dependency_overrides[get_llm_image_router] = lambda: service
    app.dependency_overrides[get_current_identity] = lambda: object()

    try:
        response = await client.post(
            "/api/v1/responses/image",
            json={},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    service.call_llm.assert_not_awaited()