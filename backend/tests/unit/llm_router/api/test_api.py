from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.llm_router.api.v1.ai_models import add_model, delete_model, get_models
from src.llm_router.api.v1.llm import invoke, invoke_text
from src.llm_router.schemas import AIModelSchema
from src.llm_service import (
    LLMImageRequest,
    LLMImageResponse,
    LLMTextRequest,
    LLMTextResponse,
)


@pytest.mark.asyncio
async def test_invoke_text_calls_service() -> None:
    service = AsyncMock()
    identity = object()
    schema = LLMTextRequest(
        input=[{"content": "Проверка"}],
    )
    expected = LLMTextResponse(
        raw_text="Ответ",
        total_tokens=5,
    )
    service.call_llm.return_value = expected

    result = await invoke_text(
        schema=schema,
        service=service,
        _identity=identity,
        model="gpt-5-mini",
    )

    assert result is expected
    service.call_llm.assert_awaited_once_with(
        schema=schema,
        model="gpt-5-mini",
    )


@pytest.mark.asyncio
async def test_invoke_image_calls_service() -> None:
    service = AsyncMock()
    identity = object()
    schema = LLMImageRequest(prompt="Нарисуй схему")
    expected = LLMImageResponse(
        size="1024x1024",
        image="base64-image",
        total_tokens=5,
    )
    service.call_llm.return_value = expected

    result = await invoke(
        schema=schema,
        service=service,
        _identity=identity,
        model="gpt-image-2",
    )

    assert result is expected
    service.call_llm.assert_awaited_once_with(
        schema=schema,
        model="gpt-image-2",
    )


@pytest.mark.asyncio
async def test_add_model_creates_model_and_commits() -> None:
    repository = AsyncMock()
    session = AsyncMock()
    created_model = object()
    repository.create.return_value = created_model

    schema = AIModelSchema(
        name="gpt-5-mini",
        description="Test model",
        context=128000,
    )

    result = await add_model(
        schema=schema,
        repository=repository,
        session=session,
    )

    assert result is created_model
    repository.create.assert_awaited_once()

    model = repository.create.await_args.args[0]
    assert model.name == "gpt-5-mini"
    assert model.description == "Test model"
    assert model.context == 128000

    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_models_calls_repository() -> None:
    repository = AsyncMock()
    identity = object()
    params = object()
    expected = object()
    repository.find.return_value = expected

    result = await get_models(
        params=params,
        repository=repository,
        _identity=identity,
    )

    assert result is expected
    repository.find.assert_awaited_once_with(params)


@pytest.mark.asyncio
async def test_delete_model_deletes_and_commits() -> None:
    repository = AsyncMock()
    session = AsyncMock()
    uid = uuid4()

    await delete_model(
        uid=uid,
        session=session,
        repository=repository,
    )

    repository.delete.assert_awaited_once_with(uid)
    session.commit.assert_awaited_once()