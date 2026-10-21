# ruff: file-ignore[private-member-access]

import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.llm_router.domain.events import LLMInvocationCreated
from src.llm_router.domain.vo import LLMInvocationStatus
from src.llm_router.services import LLMImageRouter, LLMTextRouter
from src.llm_service.schemas import LLMImageRequest, LLMTextRequest
from src.shared.infra.request_context import reset_request_id, set_request_id

TOTAL_TOKENS = 20
EDIT_TOTAL_TOKENS = 9


def _text_router(client: object, publisher: AsyncMock) -> LLMTextRouter:
    return LLMTextRouter(
        ai_model_repos=AsyncMock(),
        event_publisher=publisher,
        client=client,
        wrapper=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_text_invocation_publishes_event() -> None:
    provider_response = SimpleNamespace(
        id="resp_1",
        error=None,
        model="gpt-5.4-mini",
        output=[],
        output_text="Готовый ответ",
        usage=SimpleNamespace(total_tokens=TOTAL_TOKENS),
    )
    publisher = AsyncMock()
    router = _text_router(
        SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(return_value=provider_response))),
        publisher,
    )
    schema = LLMTextRequest(input=[{"content": "Проверка"}])
    request_id = uuid4()
    token = set_request_id(request_id)
    try:
        result = await router._invoke(model="gpt-5.4-mini", schema=schema)
    finally:
        reset_request_id(token)

    assert result.raw_text == "Готовый ответ"
    event = publisher.publish.await_args.args[0]
    assert isinstance(event, LLMInvocationCreated)
    assert event.request_id == request_id
    assert event.model == "gpt-5.4-mini"
    assert event.total_tokens == TOTAL_TOKENS
    assert event.request == schema.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert event.response == result.model_dump(mode="json", exclude_none=True)


@pytest.mark.asyncio
async def test_publish_invocation_publishes_ready_event() -> None:
    publisher = AsyncMock()
    router = _text_router(SimpleNamespace(), publisher)
    event = LLMInvocationCreated(
        request_id=uuid4(),
        model="gpt-image-2",
        total_tokens=0,
        request={"prompt": "Нарисуй схему", "image_keys": ["input-key"]},
        response={"image_key": "output-key"},
        duration_ms=50,
        status=LLMInvocationStatus.COMPLETED,
    )

    await router._publish_invocation(event)

    publisher.publish.assert_awaited_once_with(event)


@pytest.mark.asyncio
async def test_failed_invocation_publishes_event_and_reraises() -> None:
    publisher = AsyncMock()
    router = _text_router(
        SimpleNamespace(
            responses=SimpleNamespace(
                create=AsyncMock(side_effect=RuntimeError("provider unavailable"))
            )
        ),
        publisher,
    )
    schema = LLMTextRequest(input=[{"content": "Проверка"}])

    with pytest.raises(RuntimeError, match="provider unavailable"):
        await router._invoke(model="gpt-5-nano", schema=schema)

    event = publisher.publish.await_args.args[0]
    assert event.status is LLMInvocationStatus.FAILED
    assert event.error == "provider unavailable"
    assert event.request == schema.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert event.response == {}
    assert event.total_tokens == 0
    assert event.duration_ms >= 0


@pytest.mark.asyncio
async def test_monitoring_publish_failure_does_not_break_llm_response() -> None:
    provider_response = SimpleNamespace(
        id="resp_2",
        error=None,
        model="gpt-5-nano",
        output=[],
        output_text="Ответ",
        usage=SimpleNamespace(total_tokens=3),
    )
    publisher = AsyncMock()
    publisher.publish.side_effect = RuntimeError("rabbit unavailable")
    router = _text_router(
        SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(return_value=provider_response))),
        publisher,
    )

    result = await router._invoke(
        model="gpt-5-nano",
        schema=LLMTextRequest(input=[{"content": "Проверка"}]),
    )

    assert result.raw_text == "Ответ"
    publisher.publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_image_invocation_publishes_response_schema() -> None:
    image_base64 = "base64-image"
    provider_response = SimpleNamespace(
        size="1024x1024",
        data=[SimpleNamespace(b64_json=image_base64)],
        output_format="png",
        usage=SimpleNamespace(total_tokens=12),
    )
    publisher = AsyncMock()
    router = LLMImageRouter(
        ai_model_repos=AsyncMock(),
        event_publisher=publisher,
        client=SimpleNamespace(),
        image_client=SimpleNamespace(images=SimpleNamespace(generate=AsyncMock(return_value=provider_response))),
        media_client=SimpleNamespace(save_image=AsyncMock(return_value="llm-outputs/output.png")),
        wrapper=AsyncMock(),
    )
    schema = LLMImageRequest(prompt="Нарисуй схему")

    result = await router._invoke_image(model="gpt-image-2", schema=schema)

    assert result.image == "llm-outputs/output.png"
    router._media_client.save_image.assert_awaited_once_with(image_base64, folder="llm-outputs")
    router._image_client.images.generate.assert_awaited_once_with(
        model="gpt-image-2",
        prompt="Нарисуй схему",
        quality="medium",
        size="1024x1024",
        output_format="png",
    )
    event = publisher.publish.await_args.args[0]
    assert event.request == schema.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert event.response == result.model_dump(mode="json", exclude_none=True)


@pytest.mark.asyncio
async def test_image_edit_decodes_base64_and_excludes_it_from_provider_request() -> None:
    image_bytes = b"input image"
    image_base64 = base64.b64encode(image_bytes).decode()
    provider_response = SimpleNamespace(
        size="1024x1024",
        data=[SimpleNamespace(b64_json="edited-image")],
        output_format="png",
        usage=SimpleNamespace(total_tokens=EDIT_TOTAL_TOKENS),
    )
    publisher = AsyncMock()
    edit = AsyncMock(return_value=provider_response)
    router = LLMImageRouter(
        ai_model_repos=AsyncMock(),
        event_publisher=publisher,
        client=SimpleNamespace(),
        image_client=SimpleNamespace(images=SimpleNamespace(edit=edit)),
        media_client=SimpleNamespace(save_image=AsyncMock(return_value="llm-outputs/edited.png")),
        wrapper=AsyncMock(),
    )
    schema = LLMImageRequest(image=[image_base64], prompt="Измени картинку")

    result = await router._invoke_image_based(model="gpt-image-2", schema=schema)

    assert result.image == "llm-outputs/edited.png"
    router._media_client.save_image.assert_awaited_once_with("edited-image", folder="llm-outputs")
    assert result.total_tokens == EDIT_TOTAL_TOKENS
    edit.assert_awaited_once_with(
        model="gpt-image-2",
        image=[image_bytes],
        prompt="Измени картинку",
        quality="medium",
        size="1024x1024",
        output_format="png",
    )
    event = publisher.publish.await_args.args[0]
    assert event.request["image"] == [image_base64]


@pytest.mark.asyncio
async def test_media_error_does_not_retry_image_generation() -> None:
    generate = AsyncMock(return_value=SimpleNamespace(
        size="1024x1024", data=[SimpleNamespace(b64_json="image")], output_format="png",
        usage=SimpleNamespace(total_tokens=12),
    ))
    publisher = AsyncMock()
    router = LLMImageRouter(
        ai_model_repos=AsyncMock(), event_publisher=publisher, client=SimpleNamespace(),
        image_client=SimpleNamespace(images=SimpleNamespace(generate=generate)),
        wrapper=AsyncMock(),
        media_client=SimpleNamespace(save_image=AsyncMock(side_effect=RuntimeError("media down"))),
    )
    with pytest.raises(RuntimeError, match="media down"):
        await router._invoke_image(model="gpt-image-2", schema=LLMImageRequest(prompt="Draw"))
    generate.assert_awaited_once()
    publisher.publish.assert_awaited_once()
    event = publisher.publish.await_args.args[0]
    assert event.status is LLMInvocationStatus.FAILED
    assert event.error == "media down"
    assert event.total_tokens == 12
    assert event.response == {}
