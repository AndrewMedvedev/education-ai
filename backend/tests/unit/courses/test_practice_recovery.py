import asyncio
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.courses.agents.external_agents.practicer import PracticerAgent
from src.courses.domain.entities import Practice
from src.courses.domain.vo import FileUploadAssignment
from src.shared.domain.exceptions import NotFoundError


@pytest.fixture
def assignment():
    return asdict(
        FileUploadAssignment(
            title="Assignment",
            description="Write a report",
            evaluation_criteria=["Correctness"],
            submission_instructions="Upload Markdown",
        )
    )


@pytest.fixture
def agent():
    return PracticerAgent(
        practice_repo=AsyncMock(),
        lesson_repo=AsyncMock(),
        transaction=AsyncMock(),
        client=object(),
    )


def setup_lesson(agent):
    user_id, module_id, lesson_id = uuid4(), uuid4(), uuid4()
    agent.lesson_repo.read.return_value = SimpleNamespace(module_id=module_id, content_blocks=[])
    return user_id, module_id, lesson_id


@pytest.mark.asyncio
async def test_get_missing_practice_returns_null_without_generating(agent):
    ids = setup_lesson(agent)
    agent.practice_repo.read_latest_file_upload.return_value = None
    assert await agent.get_latest_practice(*ids) == {
        "practice": None,
        "practice_id": None,
        "result": None,
    }
    agent.practice_repo.read_latest_file_upload.assert_awaited_once_with(*ids)
    agent.practice_repo.create.assert_not_awaited()
    agent.transaction.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("checked", [False, True])
async def test_restores_assignment_and_latest_result(agent, assignment, checked):
    ids = setup_lesson(agent)
    payload = (
        {"practice": assignment, "score": 75, "ai_feedback": "Good"} if checked else [assignment]
    )
    practice = Practice(user_id=ids[0], module_id=ids[1], lesson_id=ids[2], practice=payload)
    agent.practice_repo.read_latest_file_upload.return_value = practice
    result = await agent.get_latest_practice(*ids)
    assert result == {
        "practice": assignment,
        "practice_id": practice.id,
        "result": {"score": 75.0, "ai_feedback": "Good"} if checked else None,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["get_latest_practice", "call_agent_creator"])
@pytest.mark.parametrize("missing", [False, True])
async def test_rejects_missing_or_foreign_module_lesson_before_practice_lookup(
    agent, method, missing
):
    ids = setup_lesson(agent)
    agent.lesson_repo.read.return_value = None if missing else SimpleNamespace(module_id=uuid4())
    with pytest.raises(NotFoundError):
        await getattr(agent, method)(*ids)
    agent.practice_repo.read_latest_file_upload.assert_not_awaited()
    agent.practice_repo.lock_file_upload.assert_not_awaited()


@pytest.mark.asyncio
async def test_post_reuses_existing_without_llm(agent, assignment, monkeypatch):
    ids = setup_lesson(agent)
    practice = Practice(user_id=ids[0], module_id=ids[1], lesson_id=ids[2], practice=[assignment])
    agent.practice_repo.read_latest_file_upload.return_value = practice
    llm = AsyncMock()
    monkeypatch.setattr("src.courses.agents.external_agents.practicer.LLMTextService", llm)
    result = await agent.call_agent_creator(*ids)
    assert result["practice_id"] == practice.id
    agent.practice_repo.lock_file_upload.assert_awaited_once_with(*ids)
    agent.transaction.assert_awaited_once_with()
    agent.practice_repo.create.assert_not_awaited()
    llm.assert_not_called()


@pytest.mark.asyncio
async def test_disconnect_during_llm_still_commits_before_dependency_cleanup(
    agent, assignment, monkeypatch
):
    ids = setup_lesson(agent)
    agent.practice_repo.read_latest_file_upload.return_value = None
    agent.practice_repo.read_by_module.return_value = []
    agent.practice_repo.create.side_effect = lambda practice: practice
    entered, finish = asyncio.Event(), asyncio.Event()

    async def invoke(**kwargs):
        entered.set()
        await finish.wait()
        return SimpleNamespace(output=assignment)

    llm = SimpleNamespace(invoke=invoke)
    monkeypatch.setattr(
        "src.courses.agents.external_agents.practicer.LLMTextService", lambda **_: llm
    )
    monkeypatch.setattr(
        "src.courses.agents.external_agents.practicer.async_load_assignment_example",
        AsyncMock(return_value="Example"),
    )
    request = asyncio.create_task(agent.call_agent_creator(*ids))
    await asyncio.wait_for(entered.wait(), timeout=2)
    request.cancel()
    await asyncio.sleep(0)
    assert not request.done()
    finish.set()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(request, timeout=2)
    created = agent.practice_repo.create.await_args.args[0]
    assert created.practice[0] == assignment
    agent.transaction.assert_awaited_once_with(created)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method_name,agent_method",
    [
        ("get_practice", "get_latest_practice"),
        ("create_practice", "call_agent_creator"),
    ],
)
async def test_routes_check_access_and_use_identity(agent, method_name, agent_method):
    from src.courses.api.v1 import agents

    ids = setup_lesson(agent)
    identity = SimpleNamespace(id=ids[0])
    check_access = AsyncMock()
    handler = AsyncMock(return_value={"practice": None, "practice_id": None, "result": None})
    setattr(agent, agent_method, handler)
    route = getattr(agents, method_name)
    await route(ids[1], ids[2], agent, identity, check_access)
    check_access.assert_awaited_once_with(identity=identity, permission=agents.READ, uid=ids[1])
    handler.assert_awaited_once_with(user_id=ids[0], module_id=ids[1], lesson_id=ids[2])
    handler.reset_mock()
    check_access.side_effect = NotFoundError("No access")
    with pytest.raises(NotFoundError):
        await route(ids[1], ids[2], agent, identity, check_access)
    handler.assert_not_awaited()
