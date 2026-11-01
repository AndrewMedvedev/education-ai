"""Practice caller regression; run through tests/run_llm_tests.py only."""

import importlib.util
import json
import sys
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from pydantic import BaseModel, RootModel, TypeAdapter
from test_text_service import Harness, assert_linkage, call, outputs, reply

from src.llm_service.services import LLMTextService
from src.llm_service.strict_schema import to_strict_json_schema

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def practice_modules(monkeypatch):
    # Skip application/package assembly; keep the caller and its domain schema real.
    def stub(name, **attributes):
        module = ModuleType(name)
        module.__dict__.update(attributes)
        monkeypatch.setitem(sys.modules, name, module)
        return module

    def load(name):
        spec = importlib.util.spec_from_file_location(
            name, ROOT.joinpath(*name.split(".")).with_suffix(".py")
        )
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        return module

    for name in (
        "src.courses",
        "src.courses.domain",
        "src.courses.application",
        "src.courses.infra",
        "src.courses.infra.services",
        "src.courses.agents",
        "src.courses.agents.external_agents",
        "src.courses.agents.course_generator",
        "src.courses.agents.course_generator.subagents",
    ):
        stub(name).__path__ = [str(ROOT.joinpath(*name.split(".")))]

    enums = load("src.courses.domain.enums")
    vo = load("src.courses.domain.vo")
    stub("src.core.others", thread_executor=None)
    stub("src.shared.application.transaction", Transaction=Mock)
    stub("src.shared.domain.exceptions", NotFoundError=RuntimeError)
    stub("src.shared.utils.time", current_datetime=Mock())
    stub("src.courses.application.repos", LessonRepository=Mock, PracticeRepository=Mock)
    stub(
        "src.courses.domain.entities",
        Practice=lambda **kwargs: SimpleNamespace(id=uuid4(), **kwargs),
    )
    stub(
        "src.courses.domain.events",
        LessonProgressUpdate=Mock,
        LessonProgressUpdated=Mock,
    )
    stub("src.courses.infra.services.client", SrvCourseClient=Mock)
    stub("src.courses.agents.schemas", PracticeResult=Mock)
    stub(
        "src.courses.agents.prompts",
        ASSIGNMENT_PROMPT="main",
        PRACTICE_FILE_CHECKER_PROMPT="synthetic checker",
    )
    stub(
        "src.courses.agents.course_generator.subagents.prompts",
        ASSIGNMENT_CREATOR_SYSTEM_PROMPT="synthetic creator",
    )
    monkeypatch.setattr(
        sys.modules["src.llm_service"], "LLMTextService", LLMTextService, raising=False
    )
    caller = load("src.courses.agents.external_agents.practicer")
    monkeypatch.setattr(caller, "async_load_assignment_example", AsyncMock(return_value="example"))
    return SimpleNamespace(caller=caller, vo=vo, enums=enums)


@pytest.fixture
def assignment():
    return {
        "assignment_type": "file_upload",
        "title": "Synthetic practice",
        "description": "Prepare a short report.",
        "evaluation_criteria": ["Explain the result"],
        "passing_score": 61,
        "allowed_extensions": [".pdf"],
        "submission_instructions": "Upload the report.",
    }


def make_agent(modules, harness, monkeypatch):
    invoke = AsyncMock(wraps=harness.service.invoke)
    monkeypatch.setattr(harness.service, "invoke", invoke)
    monkeypatch.setattr(modules.caller, "LLMTextService", Mock(return_value=harness.service))
    practice_repo = SimpleNamespace(
        read_by_module=AsyncMock(return_value=None),
        create=AsyncMock(side_effect=lambda practice: practice),
    )
    agent = modules.caller.PracticerAgent(
        practice_repo=practice_repo,
        lesson_repo=SimpleNamespace(
            read=AsyncMock(return_value=SimpleNamespace(content_blocks=[]))
        ),
        transaction=AsyncMock(),
        client=Mock(),
    )
    return agent, invoke


@pytest.mark.asyncio
async def test_actual_practice_caller_passes_root_model_and_persists_flat_assignment(
    practice_modules, assignment, monkeypatch
):
    h = Harness([reply("practice", call("final", arguments=json.dumps(assignment)))])
    agent, invoke = make_agent(practice_modules, h, monkeypatch)
    user_id, module_id, lesson_id = uuid4(), uuid4(), uuid4()

    result = await agent._create_or_reuse(user_id, module_id, lesson_id)

    invoke.assert_awaited_once()
    schema = invoke.await_args.kwargs["schema"]
    assert issubclass(schema, BaseModel)
    assert schema is RootModel[practice_modules.vo.FileUploadAssignment]
    assert isinstance(result["practice"], practice_modules.vo.FileUploadAssignment)
    assert asdict(result["practice"]) == assignment
    created = agent.practice_repo.create.await_args.args[0]
    assert (created.user_id, created.module_id, created.lesson_id) == (
        user_id,
        module_id,
        lesson_id,
    )
    assert created.practice == [assignment]
    assert result["practice_id"] == created.id
    agent.transaction.assert_awaited_once_with(created)
    parameters = h.requests["main"][0]["tools"][0]["parameters"]
    assert set(parameters["properties"]) == set(assignment)
    assert "root" not in parameters["properties"]
    h.create.assert_awaited_once()


def test_domain_dataclass_requires_wrapper_and_produces_flat_strict_schema(practice_modules):
    domain = practice_modules.vo.FileUploadAssignment
    assert is_dataclass(domain)
    assert not issubclass(domain, BaseModel)
    with pytest.raises(TypeError, match="BaseModel"):
        to_strict_json_schema(domain)

    schema = to_strict_json_schema(RootModel[domain])
    names = {field.name for field in fields(domain)}
    assert schema["type"] == "object"
    assert set(schema["properties"]) == names
    assert set(schema["required"]) == names
    assert schema["additionalProperties"] is False
    assert "root" not in schema["properties"]
    assert schema["properties"]["evaluation_criteria"]["type"] == "array"
    assert schema["properties"]["allowed_extensions"]["type"] == "array"


@pytest.mark.asyncio
async def test_real_service_output_roundtrips_domain_defaults_without_root_wrapper(
    practice_modules, assignment
):
    domain = practice_modules.vo.FileUploadAssignment
    payload = {
        key: value
        for key, value in assignment.items()
        if key not in {"assignment_type", "passing_score", "allowed_extensions"}
    }
    h = Harness([reply("defaults", call("final", arguments=json.dumps(payload)))])

    result = await h.invoke(schema=RootModel[domain])

    assert result.output == payload  # Service preserves provider JSON, not a model dump.
    adapter = TypeAdapter(domain)
    practice = adapter.validate_python(result.output)
    assert type(practice) is domain
    assert practice.assignment_type is practice_modules.vo.AssignmentType.FILE_UPLOAD
    assert practice.passing_score == 61
    assert practice.allowed_extensions == ["*"]
    assert adapter.validate_json(adapter.dump_json(practice)) == practice
    assert RootModel[domain].model_validate(result.output).root == practice
    assert "root" not in json.loads(adapter.dump_json(practice))
    assert result.tool_calls == []
    h.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_actual_practice_caller_recovers_from_schema_feedback_before_persisting(
    practice_modules, assignment, monkeypatch
):
    invalid = {**assignment, "passing_score": "not-an-integer"}
    h = Harness(
        [
            reply("invalid", call("bad", arguments=json.dumps(invalid))),
            reply("valid", call("good", arguments=json.dumps(assignment))),
        ]
    )
    agent, invoke = make_agent(practice_modules, h, monkeypatch)

    result = await agent._create_or_reuse(uuid4(), uuid4(), uuid4())

    invoke.assert_awaited_once()
    assert h.create.await_count == 2
    feedback = json.loads(outputs(h.requests["main"][1]["input"])["bad"])
    assert "schema validation" in feedback["error"]
    assert "passing_score" in feedback["error"]
    assert "int_parsing" in feedback["error"]
    assert_linkage(h.requests["main"][1]["input"])
    assert asdict(result["practice"]) == assignment
    agent.practice_repo.create.assert_awaited_once()
    agent.transaction.assert_awaited_once()
    assert agent.practice_repo.create.await_args.args[0].practice == [assignment]
