from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.courses.agents.external_agents.practicer import PracticerAgent
from src.courses.domain.entities import Practice
from src.courses.domain.events import LessonProgressUpdated
from src.courses.domain.enums import PracticeStatus
from src.shared.application.transaction import Transaction
from src.shared.domain.exceptions import NotFoundError


@pytest.mark.asyncio
async def test_call_agent_checker_marks_practice_completed_and_publishes_progress_event(monkeypatch):
    """Сохраняет успешную практику и публикует событие обновления progress."""
    practice_repo = AsyncMock()
    event_publisher = AsyncMock()
    session = AsyncMock()
    user_id = uuid4()
    lesson_id = uuid4()
    practice = Practice(user_id=user_id, module_id=uuid4(), lesson_id=lesson_id)
    practice_repo.exists.return_value = True
    practice_repo.update.return_value = practice
    checker = AsyncMock()
    checker.invoke.return_value = SimpleNamespace(output={"score": 100})
    monkeypatch.setattr(
        "src.courses.agents.external_agents.practicer.LLMTextService",
        lambda **_: checker,
    )
    agent = PracticerAgent(
        practice_repo=practice_repo,
        lesson_repo=AsyncMock(),
        transaction=Transaction(session, event_publisher),
        client=object(),
    )

    await agent.call_agent_checker({"task": "write code"}, b"solution", practice.id)

    practice_repo.exists.assert_awaited_once_with(practice.id)
    assert practice_repo.update.await_args.kwargs["status"] == PracticeStatus.COMPLETED
    session.commit.assert_awaited_once_with()
    event = event_publisher.publish_all.await_args.args[0][0]
    assert isinstance(event, LessonProgressUpdated)
    assert event.user_id == user_id
    assert event.lesson_id == lesson_id
    assert event.progress.practice_completed_at is not None
    assert practice._events == []


@pytest.mark.asyncio
async def test_call_agent_checker_marks_practice_failed_without_progress_event(monkeypatch):
    """Сохраняет неуспешную практику, не отмечая урок завершённым."""
    practice_repo = AsyncMock()
    event_publisher = AsyncMock()
    session = AsyncMock()
    practice = Practice(user_id=uuid4(), module_id=uuid4(), lesson_id=uuid4())
    practice_repo.exists.return_value = True
    practice_repo.update.return_value = practice
    checker = AsyncMock()
    checker.invoke.return_value = SimpleNamespace(output={"score": 0})
    monkeypatch.setattr(
        "src.courses.agents.external_agents.practicer.LLMTextService",
        lambda **_: checker,
    )
    agent = PracticerAgent(
        practice_repo=practice_repo,
        lesson_repo=AsyncMock(),
        transaction=Transaction(session, event_publisher),
        client=object(),
    )

    await agent.call_agent_checker({"task": "write code"}, b"solution", practice.id)

    assert practice_repo.update.await_args.kwargs["status"] == PracticeStatus.FAILED
    session.commit.assert_awaited_once_with()
    event_publisher.publish_all.assert_awaited_once_with([])


@pytest.mark.asyncio
async def test_call_agent_checker_rejects_unknown_practice_before_llm(monkeypatch):
    practice_repo = AsyncMock()
    practice_repo.exists.return_value = False
    checker = AsyncMock()
    monkeypatch.setattr("src.courses.agents.external_agents.practicer.LLMTextService", checker)
    agent = PracticerAgent(
        practice_repo=practice_repo,
        lesson_repo=AsyncMock(),
        transaction=AsyncMock(),
        client=object(),
    )

    with pytest.raises(NotFoundError, match="Practice was not found"):
        await agent.call_agent_checker({}, b"solution", uuid4())

    checker.assert_not_called()
    practice_repo.update.assert_not_awaited()
    agent.transaction.assert_not_awaited()
