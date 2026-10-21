# ruff: file-ignore[private-member-access]

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.llm_router import services
from src.llm_router.services import (
    BASE_MODEL_CONTEXT,
    PAGINATION_SIZE,
    LLMImageRouter,
    LLMTextRouter,
)
from src.llm_service.schemas import (
    LLMImageRequest,
    LLMImageResponse,
    LLMTextRequest,
    LLMTextResponse,
)
from src.shared.application.dtos import Page

MODELS = [
    {"name": "small-model", "context": 100_000},
    {"name": "large-model", "context": 500_000},
]


def _page() -> Page[dict[str, int | str]]:
    return Page.create(MODELS, total=len(MODELS), page=1, size=PAGINATION_SIZE)


def _text_router() -> tuple[LLMTextRouter, AsyncMock, AsyncMock]:
    repository = AsyncMock()
    wrapper = AsyncMock(return_value=_page())
    router = LLMTextRouter(
        ai_model_repos=repository,
        event_publisher=AsyncMock(),
        client=SimpleNamespace(),
        wrapper=wrapper,
    )
    return router, repository, wrapper


def _image_router() -> tuple[LLMImageRouter, AsyncMock, AsyncMock]:
    repository = AsyncMock()
    wrapper = AsyncMock(return_value=_page())
    router = LLMImageRouter(
        ai_model_repos=repository,
        event_publisher=AsyncMock(),
        client=SimpleNamespace(),
        image_client=SimpleNamespace(),
        media_client=AsyncMock(),
        wrapper=wrapper,
    )
    return router, repository, wrapper


@pytest.mark.asyncio
async def test_text_router_loads_models_selects_model_and_invokes_llm() -> None:
    router, repository, wrapper = _text_router()
    schema = LLMTextRequest(input=[{ "content": "Объясни async await"}])
    expected = LLMTextResponse(raw_text="Ответ", total_tokens=4)
    router._select_model_by_length = AsyncMock(return_value=("small-model", MODELS))
    router._resolve_model = AsyncMock(return_value="large-model")
    router._invoke = AsyncMock(return_value=expected)

    result = await router.call_llm(schema=schema, model="requested-model")

    assert result is expected
    wrapper.assert_awaited_once()
    assert wrapper.await_args.kwargs["func"] == repository.read_fields
    assert wrapper.await_args.kwargs["params"].size == PAGINATION_SIZE
    router._select_model_by_length.assert_awaited_once_with(
        input_messages=schema.model_dump_json(exclude_none=True, by_alias=True),
        models=MODELS,
    )
    router._resolve_model.assert_awaited_once_with(
        schema=schema,
        models=MODELS,
        selected_model="small-model",
        requested_model="requested-model",
    )
    router._invoke.assert_awaited_once_with(model="large-model", schema=schema)


@pytest.mark.asyncio
async def test_text_router_propagates_invoke_error() -> None:
    router, _, _ = _text_router()
    schema = LLMTextRequest(input=[{"content": "Проверка"}])

    router._select_model_by_length = AsyncMock(
        return_value=("small-model", MODELS)
    )
    router._resolve_model = AsyncMock(return_value="small-model")
    router._invoke = AsyncMock(side_effect=RuntimeError("LLM error"))

    with pytest.raises(RuntimeError, match="LLM error"):
        await router.call_llm(schema=schema)

    router._invoke.assert_awaited_once_with(
        model="small-model",
        schema=schema,
    )


@pytest.mark.asyncio
async def test_image_router_uses_generation_without_input_image() -> None:
    router, _, _ = _image_router()
    schema = LLMImageRequest(prompt="Нарисуй схему")
    expected = LLMImageResponse(
        size="1024x1024",
        image="image-base64",
        total_tokens=5,
    )
    router._select_model_by_length = AsyncMock(return_value=("small-model", MODELS))
    router._resolve_model = AsyncMock(return_value="large-model")
    router._invoke_image = AsyncMock(return_value=expected)
    router._invoke_image_based = AsyncMock()

    result = await router.call_llm(schema=schema)

    assert result is expected
    router._invoke_image.assert_awaited_once_with(model="large-model", schema=schema)
    router._invoke_image_based.assert_not_awaited()


@pytest.mark.asyncio
async def test_image_router_uses_editing_with_input_image() -> None:
    router, _, _ = _image_router()
    schema = LLMImageRequest(image=["aW1hZ2U="], prompt="Измени картинку")
    expected = LLMImageResponse(
        size="1024x1024",
        image="image-base64",
        total_tokens=5,
    )
    router._select_model_by_length = AsyncMock(return_value=("small-model", MODELS))
    router._resolve_model = AsyncMock(return_value="large-model")
    router._invoke_image = AsyncMock()
    router._invoke_image_based = AsyncMock(return_value=expected)

    result = await router.call_llm(schema=schema)

    assert result is expected
    router._invoke_image_based.assert_awaited_once_with(model="large-model", schema=schema)
    router._invoke_image.assert_not_awaited()


@pytest.mark.asyncio
async def test_image_router_propagates_invoke_error() -> None:
    router, _, _ = _image_router()
    schema = LLMImageRequest(prompt="Нарисуй схему")

    router._select_model_by_length = AsyncMock(
        return_value=("small-model", MODELS)
    )
    router._resolve_model = AsyncMock(return_value="small-model")
    router._invoke_image = AsyncMock(side_effect=RuntimeError("Image error"))
    router._invoke_image_based = AsyncMock()

    with pytest.raises(RuntimeError, match="Image error"):
        await router.call_llm(schema=schema)

    router._invoke_image.assert_awaited_once_with(
        model="small-model",
        schema=schema,
    )
    router._invoke_image_based.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_model_uses_fallback_for_requested_model() -> None:
    router, _, _ = _text_router()
    router._fallback_model = AsyncMock(return_value="requested-model")
    router._choose_model = AsyncMock()

    result = await router._resolve_model(
        schema={"input": "Проверка"},
        models=MODELS,
        selected_model="small-model",
        requested_model="requested-model",
    )

    assert result == "requested-model"
    router._fallback_model.assert_awaited_once_with(
        model="requested-model",
        schema={"input": "Проверка"},
        models=MODELS,
        selected_model="small-model",
    )
    router._choose_model.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_model_uses_automatic_selection_without_requested_model() -> None:
    router, _, _ = _text_router()
    router._fallback_model = AsyncMock()
    router._choose_model = AsyncMock(return_value="large-model")

    result = await router._resolve_model(
        schema={"input": "Проверка"},
        models=MODELS,
        selected_model="small-model",
    )

    assert result == "large-model"
    router._choose_model.assert_awaited_once_with(
        schema={"input": "Проверка"},
        models=MODELS,
        selected_model="small-model",
    )
    router._fallback_model.assert_not_awaited()


@pytest.mark.asyncio
async def test_fallback_model_keeps_available_requested_model() -> None:
    router, _, _ = _text_router()
    router._invoke = AsyncMock()

    result = await router._fallback_model(
        model="large-model",
        schema={"input": "Проверка"},
        models=MODELS,
        selected_model="small-model",
    )

    assert result == "large-model"
    router._invoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_fallback_model_returns_model_selected_by_llm() -> None:
    router, _, _ = _text_router()
    router._invoke = AsyncMock(
        return_value=LLMTextResponse(
            output={"model_name": "large-model"},
            total_tokens=2,
        )
    )

    result = await router._fallback_model(
        model="unknown-model",
        schema={"input": "Проверка"},
        models=MODELS,
        selected_model="small-model",
    )

    assert result == "large-model"
    router._invoke.assert_awaited_once()
    assert router._invoke.await_args.kwargs["model"] == "small-model"


@pytest.mark.asyncio
async def test_choose_model_returns_model_name_from_llm_response() -> None:
    router, _, _ = _text_router()
    router._invoke = AsyncMock(
        return_value=LLMTextResponse(
            output={"model_name": "large-model"},
            total_tokens=2,
        )
    )

    result = await router._choose_model(
        schema={"input": "Проверка"},
        models=MODELS,
        selected_model="small-model",
    )

    assert result == "large-model"
    router._invoke.assert_awaited_once()
    assert router._invoke.await_args.kwargs["model"] == "small-model"


@pytest.mark.asyncio
async def test_select_model_by_length_uses_default_for_short_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def encode(*, text: str) -> range:
        del text
        return range(10)

    monkeypatch.setattr(services.tokens_encoder, "encode", encode)

    selected_model, filtered_models = await LLMTextRouter._select_model_by_length(
        input_messages="короткий запрос",
        models=MODELS,
    )

    assert selected_model == services.settings.text_ai_model
    assert filtered_models == MODELS


@pytest.mark.asyncio
async def test_select_model_by_length_filters_models_for_long_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def encode(*, text: str) -> range:
        del text
        return range(BASE_MODEL_CONTEXT)

    monkeypatch.setattr(
        services.tokens_encoder,
        "encode",
        encode,
    )

    selected_model, filtered_models = await LLMTextRouter._select_model_by_length(
        input_messages="длинный запрос",
        models=MODELS,
    )

    assert selected_model == "large-model"
    assert filtered_models == [MODELS[1]]
