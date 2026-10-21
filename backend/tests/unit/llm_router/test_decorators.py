# ruff: file-ignore[private-member-access, unused-async, unused-function-argument]

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from src.llm_router.decorators import track_image_invocation, track_text_invocation
from src.llm_router import decorators
from src.llm_router.domain.vo import LLMInvocationStatus
from src.llm_service.schemas import (
    LLMImageRequest,
    LLMImageResponse,
    LLMTextRequest,
    LLMTextResponse,
)


@track_text_invocation
async def _successful_text_call(
    target: SimpleNamespace,
    model: str,
    schema: LLMTextRequest,
) -> LLMTextResponse:
    return target.result


@track_text_invocation
async def _failing_text_call(
    _target: SimpleNamespace,
    model: str,
    schema: LLMTextRequest,
) -> LLMTextResponse:
    del model, schema
    raise RuntimeError("LLM unavailable")


@track_image_invocation
async def _successful_image_call(
    target: SimpleNamespace,
    model: str,
    schema: LLMImageRequest,
) -> LLMImageResponse:
    return target.result


@pytest.mark.asyncio
async def test_track_text_invocation_publishes_success() -> None:
    result = LLMTextResponse(raw_text="Готовый ответ", total_tokens=8)
    target = SimpleNamespace(result=result, _publish_invocation=AsyncMock())
    schema = LLMTextRequest(
    input=[{"content": "Проверь текст"}]
    )

    returned_result = await _successful_text_call(target, "gpt-5-mini", schema)

    assert returned_result is result
    target._publish_invocation.assert_awaited_once()
    event = target._publish_invocation.await_args.args[0]
    assert event.model == "gpt-5-mini"
    assert event.request == schema.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert event.response == result.model_dump(mode="json", exclude_none=True)
    assert event.status is LLMInvocationStatus.COMPLETED
    assert event.duration_ms >= 0
    assert event.error is None


@pytest.mark.asyncio
async def test_track_text_invocation_publishes_failure_and_reraises() -> None:
    target = SimpleNamespace(_publish_invocation=AsyncMock())
    schema = LLMTextRequest(
    input=[{"content": "Проверь текст"}]
)
    with pytest.raises(RuntimeError, match="LLM unavailable"):
        await _failing_text_call(target, "gpt-5-mini", schema)

    target._publish_invocation.assert_awaited_once()
    event = target._publish_invocation.await_args.args[0]
    assert event.request == schema.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert event.status is LLMInvocationStatus.FAILED
    assert event.error == "LLM unavailable"
    assert event.duration_ms >= 0


@pytest.mark.asyncio
async def test_track_image_invocation_publishes_success() -> None:
    result = LLMImageResponse(
        size="1024x1024",
        image="base64-image",
        total_tokens=12,
    )
    media = SimpleNamespace(save_image=AsyncMock(return_value="llm-outputs/image.png"))
    target = SimpleNamespace(result=result, _publish_invocation=AsyncMock(), _media_client=media)
    schema = LLMImageRequest(prompt="Нарисуй схему")

    returned_result = await _successful_image_call(target, "gpt-image-2", schema)

    assert returned_result is result
    assert result.image == "llm-outputs/image.png"
    media.save_image.assert_awaited_once_with("base64-image", folder="llm-outputs")
    event = target._publish_invocation.await_args.args[0]
    assert event.request == schema.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert event.response == result.model_dump(mode="json", exclude_none=True)
    assert event.status is LLMInvocationStatus.COMPLETED


@pytest.mark.asyncio
async def test_text_invocation_generates_request_id_when_context_is_empty(
    monkeypatch,
):
    publisher = AsyncMock()
    router = AsyncMock()
    router._publish_invocation = publisher

    result = LLMTextResponse(
        output={"result": "test"},
        raw_text=None,
        tool_calls=[],
        messages=[],
        total_tokens=10,
    )

    async def invoke(*args, **kwargs):
        return result

    router.invoke = invoke

    decorated = track_text_invocation(invoke)

    monkeypatch.setattr(
        decorators,
        "get_request_id",
        lambda: None,
    )

    request = LLMTextRequest(
        input=[{"content": "Проверка"}],
    )

    await decorated(
        router,
        model="test-model",
        schema=request,
    )

    event = publisher.await_args.args[0]

    assert isinstance(event.request_id, UUID)
    assert event.model == "test-model"
    assert event.status == LLMInvocationStatus.COMPLETED

@pytest.mark.asyncio
async def test_track_image_invocation_publishes_failure_and_reraises() -> None:
    async def failing_call(
        _target: SimpleNamespace,
        model: str,
        schema: LLMImageRequest,
    ) -> LLMImageResponse:
        del model, schema
        raise RuntimeError("Image generation failed")

    decorated = track_image_invocation(failing_call)

    target = SimpleNamespace(_publish_invocation=AsyncMock())
    schema = LLMImageRequest(prompt="Нарисуй схему")

    with pytest.raises(RuntimeError, match="Image generation failed"):
        await decorated(
            target,
            model="gpt-image-2",
            schema=schema,
        )

    target._publish_invocation.assert_awaited_once()

    event = target._publish_invocation.await_args.args[0]

    assert event.request == schema.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )
    assert event.status is LLMInvocationStatus.FAILED
    assert event.error == "Image generation failed"
    assert event.total_tokens == 0
    assert event.duration_ms >= 0
