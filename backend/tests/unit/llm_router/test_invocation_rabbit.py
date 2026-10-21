from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.llm_router.domain.events import LLMInvocationCreated
from src.llm_router.domain.vo import LLMInvocationStatus
from src.llm_router.infra.invocation_rabbit import on_llm_invocation_created


@pytest.mark.asyncio
async def test_consumer_creates_invocation_and_commits() -> None:
    event = LLMInvocationCreated(
        request_id=uuid4(),
        model="gpt-5-mini",
        total_tokens=42,
        request={"input": "Проверка"},
        response={"raw_text": "Готово"},
        duration_ms=120,
        status=LLMInvocationStatus.COMPLETED,
    )
    repository = AsyncMock()
    session = AsyncMock()

    await on_llm_invocation_created(
        event=event,
        repository=repository,
        session=session,
        media_client=AsyncMock(),
    )

    repository.create.assert_awaited_once()
    invocation = repository.create.await_args.args[0]
    assert invocation.id == event.event_id
    assert invocation.request_id == event.request_id
    assert invocation.model == event.model
    assert invocation.total_tokens == event.total_tokens
    assert invocation.request == event.request
    assert invocation.response == event.response
    assert invocation.duration_ms == event.duration_ms
    assert invocation.status is event.status
    assert invocation.error is None
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [LLMInvocationStatus.COMPLETED, LLMInvocationStatus.FAILED])
async def test_input_images_are_saved_as_keys_for_both_statuses(status) -> None:
    images = [f"base64-{index}" for index in range(5)]
    keys = [f"llm-inputs/{index}.png" for index in range(5)]
    event = LLMInvocationCreated(
        request_id=uuid4(), model="gpt-image-2", total_tokens=0,
        request={"image": images, "prompt": "Draw"}, response={}, duration_ms=10, status=status,
    )
    media = AsyncMock()
    media.save_image.side_effect = keys
    repo = AsyncMock()
    session = AsyncMock()

    await on_llm_invocation_created(event, repo, session, media)

    assert media.save_image.await_count == len(images)
    assert repo.create.await_args.args[0].request == {"image": keys, "prompt": "Draw"}
    assert repo.create.await_args.args[0].status is status
    assert event.request["image"] == images
    session.commit.assert_awaited_once()
