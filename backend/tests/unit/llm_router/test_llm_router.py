# ruff: file-ignore[private-member-access, unused-async, unused-function-argument]

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.llm_router.domain.events import LLMInvocationCreated
from src.llm_router import services
from src.llm_router.domain.vo import LLMInvocationStatus
from src.llm_router.services import (
    LLMRouter,
)
from src.llm_service.schemas import LLMTextRequest, LLMTextResponse


@pytest.mark.asyncio
async def test_publish_invocation_does_not_raise_on_publisher_error():
    publisher = AsyncMock()
    publisher.publish.side_effect = Exception("RabbitMQ error")

    router = LLMRouter(
        ai_model_repos=AsyncMock(),
        event_publisher=publisher,
        client=AsyncMock(),
        wrapper=AsyncMock(),
    )

    event = LLMInvocationCreated(
        request_id=uuid4(),
        model="test-model",
        total_tokens=10,
        request={},
        response={},
        duration_ms=100,
        status=LLMInvocationStatus.COMPLETED,
    )

    await router._publish_invocation(event)

    publisher.publish.assert_awaited_once_with(event)


@pytest.mark.asyncio
async def test_invoke_retries_after_error(monkeypatch):
    client = AsyncMock()
    router = LLMRouter(
        ai_model_repos=AsyncMock(),
        event_publisher=AsyncMock(),
        client=client,
        wrapper=AsyncMock(),
    )

    client.responses.create.side_effect = [
        Exception("temporary error"),
        object(),
    ]

    expected_result = LLMTextResponse(
        output=None,
        raw_text="test",
        tool_calls=[],
        messages=[],
        total_tokens=10,
    )

    monkeypatch.setattr(
        services,
        "parse_llm_response",
        lambda **kwargs: expected_result,
    )

    monkeypatch.setattr(
        services,
        "wait_strategy",
        lambda retry_state: 0,
    )

    schema = LLMTextRequest(
        input=[{"role": "user", "content": "test"}],
    )

    result = await router._invoke(
        model="test-model",
        schema=schema,
    )

    assert result == expected_result
    assert client.responses.create.await_count == 2


@pytest.mark.asyncio
async def test_invoke_raises_error_after_retries():
    client = AsyncMock()
    router = LLMRouter(
        ai_model_repos=AsyncMock(),
        event_publisher=AsyncMock(),
        client=client,
        wrapper=AsyncMock(),
    )

    error = Exception("temporary error")
    client.responses.create.side_effect = error

    schema = LLMTextRequest(
        input=[{"role": "user", "content": "test"}],
    )

    with pytest.raises(Exception, match="temporary error"):
        await router._invoke(
            model="test-model",
            schema=schema,
        )

    assert client.responses.create.await_count == 3


@pytest.mark.asyncio
async def test_invoke_passes_request_to_client(monkeypatch):
    client = AsyncMock()
    router = LLMRouter(
        ai_model_repos=AsyncMock(),
        event_publisher=AsyncMock(),
        client=client,
        wrapper=AsyncMock(),
    )

    response = object()
    client.responses.create.return_value = response

    expected_result = LLMTextResponse(
        output=None,
        raw_text="test",
        tool_calls=[],
        messages=[],
        total_tokens=10,
    )

    monkeypatch.setattr(
        services,
        "parse_llm_response",
        lambda **kwargs: expected_result,
    )

    schema = LLMTextRequest(
        input=[{"role": "user", "content": "test"}],
    )

    result = await router._invoke(
        model="test-model",
        schema=schema,
    )

    assert result == expected_result

    client.responses.create.assert_awaited_once_with(
        model="test-model",
        input=[{"role": "user", "content": "test"}],
    )

