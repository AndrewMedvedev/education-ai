import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel


class GenerationContext(BaseModel):
    user_id: UUID
    course_id: UUID
    prompt: str


class Runtime:
    def __class_getitem__(cls, _item):
        return cls


@pytest.fixture
def course_tools(monkeypatch):
    """Внешние клиенты подменены; проверяется тело настоящего complete_interview."""
    for name in [
        "isolated_courses",
        "isolated_courses.agents",
        "isolated_courses.infra",
        "isolated_courses.infra.database",
        "isolated_courses.infra.database.repos",
        "isolated_courses.agents.course_generator",
        "src",
        "src.llm_service",
    ]:
        module = ModuleType(name)
        module.__path__ = []
        monkeypatch.setitem(sys.modules, name, module)
    sdk = sys.modules["src.llm_service"]
    sdk.Runtime = Runtime
    sdk.tool = lambda **_kwargs: lambda function: function
    schemas = ModuleType("isolated_courses.agents.schemas")
    schemas.Context = GenerationContext
    schemas.GenerationContext = GenerationContext
    schemas.RuntimeContext = Runtime
    monkeypatch.setitem(sys.modules, schemas.__name__, schemas)
    repository = ModuleType("isolated_courses.infra.database.repos.document")
    repository.SqlDocumentRepository = MagicMock()
    monkeypatch.setitem(sys.modules, repository.__name__, repository)
    workflow = ModuleType("isolated_courses.agents.course_generator.workflow")
    workflow.generate_course = SimpleNamespace(kiq=AsyncMock())
    monkeypatch.setitem(sys.modules, workflow.__name__, workflow)
    path = Path(__file__).resolve().parents[3] / "src/courses/agents/tools.py"
    spec = importlib.util.spec_from_file_location("isolated_courses.agents.tools", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.generate_course = workflow.generate_course
    return module


@pytest.mark.asyncio
async def test_complete_interview_awaits_taskiq_and_returns_task_id(course_tools):
    user_id, course_id = uuid4(), uuid4()
    runtime = SimpleNamespace(
        context=SimpleNamespace(user_id=user_id, course_id=course_id),
        state=SimpleNamespace(task_id=None),
    )
    course_tools.generate_course.kiq.return_value = SimpleNamespace(task_id="taskiq-id")
    result = await course_tools.send_course_for_generation("prompt", runtime)
    course_tools.generate_course.kiq.assert_awaited_once_with(
        context=GenerationContext(user_id=user_id, course_id=course_id, prompt="prompt"),
    )
    assert runtime.state.task_id == "taskiq-id"
    assert "task_id=taskiq-id" in result


@pytest.mark.asyncio
async def test_queue_failure_does_not_report_success(course_tools):
    runtime = SimpleNamespace(
        context=SimpleNamespace(user_id=uuid4(), course_id=uuid4()),
        state=SimpleNamespace(task_id=None),
    )
    course_tools.generate_course.kiq.side_effect = ConnectionError("Test broker failure")
    with pytest.raises(ConnectionError, match="Test broker failure"):
        await course_tools.send_course_for_generation("prompt", runtime)
    assert runtime.state.task_id is None
