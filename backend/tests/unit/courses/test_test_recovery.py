import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.courses.agents.external_agents.tester import TesterAgent
from src.courses.domain.entities import Practice
from src.courses.domain.enums import PracticeStatus
from src.shared.domain.exceptions import NotFoundError


@pytest.fixture
def agent():
    return TesterAgent(AsyncMock(), AsyncMock(), AsyncMock(), object())


@pytest.mark.asyncio
async def test_reuses_latest_unfinished_test(agent, monkeypatch):
    ids = uuid4(), uuid4(), uuid4()
    agent.lesson_repo.read.return_value = SimpleNamespace(module_id=ids[1])
    test = {"test_type": "multiple_choice", "questions": []}
    existing = Practice(user_id=ids[0], module_id=ids[1], lesson_id=ids[2], practice=[test])
    agent.practice_repo.read_latest_knowledge_test.return_value = existing
    llm = AsyncMock()
    monkeypatch.setattr("src.courses.agents.external_agents.tester.LLMTextService", llm)
    assert await agent.call_agent_creator(*ids) == {"practice": test, "practice_id": existing.id}
    agent.practice_repo.lock_knowledge_test.assert_awaited_once_with(*ids)
    agent.transaction.assert_awaited_once_with()
    llm.assert_not_called()


@pytest.mark.asyncio
async def test_rejects_lesson_from_another_module(agent):
    ids = uuid4(), uuid4(), uuid4()
    agent.lesson_repo.read.return_value = SimpleNamespace(module_id=uuid4())
    with pytest.raises(NotFoundError):
        await agent.call_agent_creator(*ids)
    agent.practice_repo.lock_knowledge_test.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancelled_request_waits_for_generation_and_propagates_cancel(agent, monkeypatch):
    ids = uuid4(), uuid4(), uuid4()
    agent.lesson_repo.read.return_value = SimpleNamespace(module_id=ids[1], content_blocks=[])
    previous = Practice(user_id=ids[0], module_id=ids[1], lesson_id=ids[2], status=PracticeStatus.COMPLETED)
    agent.practice_repo.read_latest_knowledge_test.return_value = previous
    agent.practice_repo.read_by_module.return_value = []
    agent.practice_repo.create.side_effect = lambda value: value
    entered, finish = asyncio.Event(), asyncio.Event()

    async def invoke(**kwargs):
        entered.set()
        await finish.wait()
        raise RuntimeError("generation failed")

    monkeypatch.setattr("src.courses.agents.external_agents.tester.LLMTextService", lambda **_: SimpleNamespace(invoke=invoke))
    request = asyncio.create_task(agent.call_agent_creator(*ids))
    await asyncio.wait_for(entered.wait(), 2)
    request.cancel()
    await asyncio.sleep(0)
    assert not request.done()
    finish.set()
    with pytest.raises(RuntimeError, match="generation failed"):
        await request
    agent.practice_repo.create.assert_not_awaited()
