"""Offline contract tests for the iterative service -> router -> parser loop.

Run via tests/run_llm_tests.py, not application-wide pytest collection. Provider
responses are scripted SDK objects; both internal HTTP DTOs cross a JSON roundtrip.
"""

import asyncio
import copy
import importlib.util
import json
from collections import Counter, defaultdict, deque
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import openai
import pytest
from openai.types.responses import (
    Response,
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
    ResponseReasoningItem,
)
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from src.llm_router.services import LLMRouter, LLMTextRouter
from src.llm_router.utils import StructuredOutputError
from src.llm_service.middleware import BaseAgentMiddleware
from src.llm_service.schemas import LLMTextRequest, LLMTextResponse, ToolCallParsed
from src.llm_service.services import BaseLLMService, LLMTextService, ModelRequestLimitError
from src.llm_service.tools import tool

FINAL = "submit_final_result"
INPUT = [{"role": "user", "content": "main"}]


class Result(BaseModel):
    value: int = Field(gt=0)


class OptionalResult(BaseModel):
    value: int | None = None


class Child(BaseModel):
    day: date = Field(alias="eventDate")


class AliasedResult(BaseModel):
    child: Child = Field(alias="nestedResult")
    labels: list[str]


def call(call_id, name=FINAL, arguments='{"value": 1}'):
    # None and malformed JSON must reach the real parser, not SDK validation.
    return ResponseFunctionToolCall.model_construct(
        id=f"fc_{call_id}",
        type="function_call",
        call_id=call_id,
        name=name,
        arguments=arguments,
        status="completed",
    )


def reply(tag, *calls, text=None, tokens=11, status="completed"):
    output = [
        ResponseReasoningItem.model_construct(
            id=f"rs_{tag}",
            type="reasoning",
            summary=[],
            encrypted_content=f"reasoning_{tag}",
        ),
        *calls,
    ]
    if text is not None:
        output.append(
            ResponseOutputMessage.model_construct(
                id=f"msg_{tag}",
                type="message",
                role="assistant",
                status="completed",
                content=[
                    ResponseOutputText.model_construct(
                        type="output_text", text=text, annotations=[]
                    )
                ],
            )
        )
    return Response.model_construct(
        id=f"resp_{tag}",
        output=output,
        status=status,
        error=None,
        usage=SimpleNamespace(total_tokens=tokens),
        incomplete_details=SimpleNamespace(reason="max_output_tokens"),
    )


def dump_items(response):

    return [
        item.model_dump(mode="json", exclude_none=True, exclude_unset=True)
        for item in response.output
    ]


def assert_linkage(messages):
    calls = Counter(m["call_id"] for m in messages if m.get("type") == "function_call")
    outputs = Counter(m["call_id"] for m in messages if m.get("type") == "function_call_output")
    assert calls == outputs, "Each historical call needs exactly one output"
    assert all(count == 1 for count in calls.values()), "call IDs must be unique"
    pending = set()
    for message in messages:
        if message.get("type") == "function_call":
            pending.add(message["call_id"])
        elif message.get("type") == "function_call_output":
            assert message["call_id"] in pending
            pending.remove(message["call_id"])


def outputs(messages):
    return {m["call_id"]: m["output"] for m in messages if m.get("type") == "function_call_output"}


class Harness:
    """Scripted provider with per-invocation histories, usable concurrently."""

    def __init__(self, script, **kwargs):
        self.scripts = {
            key: deque(value)
            for key, value in (script if isinstance(script, dict) else {"main": script}).items()
        }
        self.requests = defaultdict(list)
        self.previous = {}
        self.parsed = []
        self.http_requests = []
        self.create = AsyncMock(side_effect=self.provider)
        self.client = SimpleNamespace(
            responses=SimpleNamespace(
                create=AsyncMock(side_effect=AssertionError("unbounded SDK"))
            ),
            with_options=Mock(
                return_value=SimpleNamespace(responses=SimpleNamespace(create=self.create))
            ),
        )
        self.router = LLMTextRouter(
            ai_model_repos=Mock(),
            event_publisher=SimpleNamespace(publish=AsyncMock()),
            client=self.client,
            wrapper=AsyncMock(),
        )
        self.service = LLMTextService(client=Mock(), **kwargs)
        self.service._send_request = AsyncMock(side_effect=self.bridge)

    async def provider(self, **payload):
        assert "disable_retries" not in payload
        assert "final_tool_name" not in payload
        assert "text" not in payload  # final tool, never native text.format
        assert payload["model"] == "deepseek-v4-pro"
        messages = payload["input"]
        key = messages[0]["content"]
        assert_linkage(messages)
        if key in self.previous:
            previous_input, previous_response = self.previous[key]
            prefix = previous_input + dump_items(previous_response)
            assert messages[: len(prefix)] == prefix, "History/reasoning must survive unchanged"
        self.requests[key].append(copy.deepcopy(payload))
        assert self.scripts[key], "Unexpected extra provider request (N+1)"
        result = self.scripts[key].popleft()
        if isinstance(result, BaseException):
            raise result
        self.previous[key] = (copy.deepcopy(messages), result)
        return result

    async def bridge(self, request, path):
        assert path.startswith("/api/v1/responses/text")
        wire = request.model_dump_json(exclude_none=True)
        self.http_requests.append(json.loads(wire))
        assert self.http_requests[-1]["disable_retries"] is True
        parsed_request = LLMTextRequest.model_validate_json(wire)
        final_tools = [t for t in (parsed_request.tools or []) if t["name"].startswith(FINAL)]
        if parsed_request.instructions and "Finish by calling" in parsed_request.instructions:
            assert parsed_request.final_tool_name == final_tools[-1]["name"]
        else:
            assert parsed_request.final_tool_name is None
        result = await self.router.call_llm(parsed_request)
        result = LLMTextResponse.model_validate_json(result.model_dump_json())
        self.parsed.append(result.model_copy(deep=True))
        return result

    async def invoke(self, schema=Result, messages=None):
        result = await self.service.invoke(copy.deepcopy(messages or INPUT), schema=schema)
        assert_linkage(result.messages)
        for options in self.client.with_options.call_args_list:
            assert options.kwargs == {"max_retries": 0}
        self.client.responses.create.assert_not_awaited()
        return result


@pytest.fixture(autouse=True)
def no_retry_sleep(monkeypatch):
    async def forbidden_sleep(*args, **kwargs):
        pytest.fail("The bounded service must not enter router retry sleep")

    monkeypatch.setattr(LLMRouter._invoke_with_retries.retry, "sleep", forbidden_sleep)


def ordinary_tool(effects, name="lookup", action=None):
    @tool(name=name)
    async def lookup(value: int = 1):
        effects.append(value)
        return await action(value) if action else {"seen": value}

    return lookup


@pytest.mark.asyncio
async def test_valid_first_final_is_one_request_and_does_not_leak_tool():
    h = Harness([reply("first", call("final"), text="provider note", tokens=27)])
    result = await h.invoke()
    assert result.output == {"value": 1}
    assert result.tool_calls == []
    assert result.raw_text == "provider note"
    assert result.total_tokens == 27
    h.create.assert_awaited_once()
    payload = h.requests["main"][0]
    final = payload["tools"][0]
    assert final["name"] == FINAL and final["strict"] is True
    assert final["parameters"]["required"] == ["value"]
    assert final["parameters"]["additionalProperties"] is False
    assert FINAL in payload["instructions"]
    assert outputs(result.messages) == {"final": "Final result accepted."}
    assert h.service.tools is None
    # A later unstructured invocation must not inherit the synthetic final tool.
    h.scripts["main"].append(reply("plain", text="plain answer"))
    h.previous.clear()
    await h.invoke(schema=None)
    assert "tools" not in h.requests["main"][-1]
    assert "instructions" not in h.requests["main"][-1]


@pytest.mark.parametrize("bad", ["{}", '{"value": 0}', '{"value": "wrong"}'])
@pytest.mark.asyncio
async def test_schema_failure_becomes_linked_feedback_then_valid_final(bad):
    h = Harness([reply("bad", call("bad", arguments=bad)), reply("ok", call("ok"))])
    result = await h.invoke()
    feedback = json.loads(outputs(h.requests["main"][1]["input"])["bad"])
    assert "schema validation" in feedback["error"]
    assert result.output == {"value": 1}
    assert h.create.await_count == 2


@pytest.mark.parametrize(
    "bad",
    [
        '{"value":',
        "garbage",
        "",
        None,
        "null",
        "[]",
        '"str"',
        "42",
        "true",
        "NaN",
        "Infinity",
        "-Infinity",
        '{"value": NaN}',
        '{"nested": [Infinity]}',
        '{"nested": {"value": -Infinity}}',
    ],
)
@pytest.mark.asyncio
async def test_invalid_json_or_top_type_cannot_turn_into_optional_empty_success(bad):
    h = Harness(
        [reply("bad", call("bad", arguments=bad)), reply("ok", call("ok", arguments="{}"))]
    )
    result = await h.invoke(OptionalResult)
    assert h.create.await_count == 2
    assert h.parsed[0].tool_calls[0].arguments == {}
    assert h.parsed[0].tool_calls[0].arguments_error
    assert "error" in json.loads(outputs(h.requests["main"][1]["input"])["bad"])
    assert result.output == {}  # validation must not inject defaults into provider JSON


@pytest.mark.asyncio
async def test_base_http_session_transmits_final_name_to_real_router_but_not_provider():
    h = Harness([reply("http_final", call("http_final"))])
    posted = []

    async def post(url, json):
        assert url == "/api/v1/responses/text"
        posted.append(copy.deepcopy(json))
        request = LLMTextRequest.model_validate(json)
        assert request.disable_retries is True
        assert request.final_tool_name == FINAL
        result = await h.router.call_llm(request)
        return SimpleNamespace(json=AsyncMock(return_value=result.model_dump(mode="json")))

    session = SimpleNamespace(post=AsyncMock(side_effect=post))

    @asynccontextmanager
    async def token_session():
        yield session

    h.service._client = SimpleNamespace(_get_token_session=token_session)
    h.service._send_request = BaseLLMService._send_request.__get__(h.service)
    result = await h.invoke()
    assert result.output == {"value": 1}
    assert posted[0]["final_tool_name"] == FINAL
    assert posted[0]["disable_retries"] is True
    assert "final_tool_name" not in h.create.await_args.kwargs
    assert "disable_retries" not in h.create.await_args.kwargs
    session.post.assert_awaited_once()
    h.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_practice_timeout_reaches_sdk_options_but_not_provider_payload():
    h = Harness([reply("timeout", call("timeout"))], request_timeout=1200)
    result = await h.service.invoke(copy.deepcopy(INPUT), schema=Result)
    assert result.output == {"value": 1}
    h.client.with_options.assert_called_with(max_retries=0, timeout=1200)
    assert "request_timeout" not in h.create.await_args.kwargs


@pytest.mark.asyncio
async def test_practice_timeout_applies_to_internal_http_request():
    h = Harness([reply("http_timeout", call("http_timeout"))], request_timeout=1200)
    posted = []

    async def post(url, json, timeout):
        posted.append(timeout.total)
        result = await h.router.call_llm(LLMTextRequest.model_validate(json))
        return SimpleNamespace(json=AsyncMock(return_value=result.model_dump(mode="json")))

    session = SimpleNamespace(post=AsyncMock(side_effect=post))

    @asynccontextmanager
    async def token_session():
        yield session

    h.service._client = SimpleNamespace(_get_token_session=token_session)
    h.service._send_request = BaseLLMService._send_request.__get__(h.service)
    result = await h.service.invoke(copy.deepcopy(INPUT), schema=Result)
    assert result.output == {"value": 1}
    assert posted == [1200]


def test_validate_final_validates_deepcopy_but_returns_original_arguments():
    class MutatingAliases(BaseModel):
        value: int = Field(validation_alias="inputValue", serialization_alias="outputValue")
        nested: dict[str, list[int]]
        omitted: str = "default"

        @model_validator(mode="before")
        @classmethod
        def mutate(cls, data):
            data["inputValue"] = int(data["inputValue"])
            data["nested"]["items"].append(99)
            return data

    original = {"inputValue": "7", "nested": {"items": [1, 2]}}
    parsed = ToolCallParsed(call_id="direct", name=FINAL, arguments=copy.deepcopy(original))
    output, error = LLMTextService._validate_final(parsed, MutatingAliases)
    assert error is None
    assert parsed.arguments == original
    assert output == original
    assert output is parsed.arguments


@pytest.mark.asyncio
async def test_original_json_preserves_validation_alias_coercible_string_and_omitted_defaults():
    class SplitAliases(BaseModel):
        value: int = Field(validation_alias="inputValue", serialization_alias="outputValue")
        defaulted: str = "must remain omitted"

    original = {"inputValue": "7"}
    assert SplitAliases.model_validate(original).model_dump(by_alias=True) == {
        "outputValue": 7,
        "defaulted": "must remain omitted",
    }
    h = Harness([reply("alias", call("alias", arguments=json.dumps(original)))])
    result = await h.invoke(SplitAliases)
    assert result.output == original
    assert result.output == h.parsed[0].tool_calls[0].arguments
    assert result.output["inputValue"] == "7"
    assert "outputValue" not in result.output and "defaulted" not in result.output
    h.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_before_validator_cannot_mutate_returned_provider_json_even_nested():
    seen = []

    class MutatingResult(BaseModel):
        value: int
        nested: dict[str, list[int]]

        @model_validator(mode="before")
        @classmethod
        def mutate_input(cls, data):
            seen.append(copy.deepcopy(data))
            data["value"] = 99
            data["nested"]["items"].append(99)
            data.pop("extra")
            return data

    original = {"value": "7", "nested": {"items": [1, 2]}, "extra": "keep original"}
    h = Harness([reply("mutation", call("mutation", arguments=json.dumps(original)))])
    result = await h.invoke(MutatingResult)
    assert seen == [original]
    assert result.output == original
    assert h.parsed[0].tool_calls[0].arguments == original
    assert (
        json.loads(
            next(m["arguments"] for m in result.messages if m.get("type") == "function_call")
        )
        == original
    )
    h.create.assert_awaited_once()


@pytest.mark.parametrize("schema", [None, Result])
@pytest.mark.parametrize("arguments", ["[]", "null", '"text"', "42", "true"])
@pytest.mark.asyncio
async def test_ordinary_nonobject_raises_before_any_tool_execution(schema, arguments):
    effects = []
    h = Harness(
        [
            reply("bad", call("ordinary", "lookup", arguments), call("otherwise_valid", "lookup")),
            reply("unused", call("unused")),
        ],
        tools={"lookup": ordinary_tool(effects)},
    )
    with pytest.raises(ValidationError) as caught:
        await h.invoke(schema)
    assert caught.value.errors()[0]["loc"] == ("arguments",)
    assert caught.value.errors()[0]["type"] == "dict_type"
    assert effects == []
    h.create.assert_awaited_once()
    assert len(h.scripts["main"]) == 1


@pytest.mark.parametrize("arguments", ['{"value":', "garbage", "", None])
@pytest.mark.asyncio
async def test_ordinary_malformed_json_retains_old_empty_dict_execution_fallback(arguments):
    effects = []
    h = Harness(
        [reply("bad", call("ordinary", "lookup", arguments)), reply("ok", call("ok"))],
        tools={"lookup": ordinary_tool(effects)},
    )
    result = await h.invoke()
    assert effects == [1]  # {} invokes the ordinary tool with its default, as before
    assert h.parsed[0].tool_calls[0].arguments == {}
    assert h.parsed[0].tool_calls[0].arguments_error
    assert json.loads(outputs(h.requests["main"][1]["input"])["ordinary"]) == {"seen": 1}
    assert result.output == {"value": 1}
    assert h.create.await_count == 2


@pytest.mark.asyncio
async def test_valid_optional_empty_object_needs_no_correction():
    h = Harness([reply("empty", call("empty", arguments="{}"))])
    assert (await h.invoke(OptionalResult)).output == {}
    h.create.assert_awaited_once()


@pytest.mark.parametrize("count", [2, 3])
@pytest.mark.asyncio
async def test_multiple_finals_reject_every_call_not_just_first(count):
    h = Harness(
        [
            reply("many", *(call(f"bad{i}") for i in range(count))),
            reply("ok", call("ok")),
        ]
    )
    await h.invoke()
    feedback = outputs(h.requests["main"][1]["input"])
    assert set(feedback) == {f"bad{i}" for i in range(count)}
    assert all("Multiple final" in json.loads(value)["error"] for value in feedback.values())


@pytest.mark.parametrize("text", ["", "ordinary text", '{"value": 1}'])
@pytest.mark.asyncio
async def test_text_uses_corrective_user_message_not_fabricated_tool_output(text):
    h = Harness([reply("text", text=text), reply("ok", call("ok"))])
    await h.invoke()
    messages = h.requests["main"][1]["input"]
    assert messages[-1]["role"] == "user"
    assert FINAL in messages[-1]["content"]
    assert outputs(messages) == {}
    assert h.create.await_count == 2


@pytest.mark.parametrize("final_count", [0, 1, 2])
@pytest.mark.asyncio
async def test_ordinary_and_mixed_calls_execute_ordinary_but_require_new_final(final_count):
    effects = []
    lookup = ordinary_tool(effects)
    h = Harness(
        [
            reply(
                "mixed",
                call("ordinary", "lookup", '{"value": 9}'),
                *(call(f"premature{i}") for i in range(final_count)),
            ),
            reply("done", call("done", arguments='{"value": 2}')),
        ],
        tools={"lookup": lookup},
    )
    result = await h.invoke()
    assert effects == [9]
    assert result.output == {"value": 2}
    feedback = outputs(h.requests["main"][1]["input"])
    assert json.loads(feedback["ordinary"]) == {"seen": 9}
    for i in range(final_count):
        assert "error" in json.loads(feedback[f"premature{i}"])
    assert len(feedback) == 1 + final_count
    assert h.service.tools == {"lookup": lookup}


@pytest.mark.asyncio
async def test_unknown_tool_gets_linked_error_and_can_recover():
    h = Harness([reply("unknown", call("unknown", "missing")), reply("ok", call("ok"))])
    await h.invoke()
    assert (
        "Unknown tool" in json.loads(outputs(h.requests["main"][1]["input"])["unknown"])["error"]
    )


@pytest.mark.parametrize("limit", [1, 2, 4])
@pytest.mark.asyncio
async def test_budget_exactly_n_no_n_plus_one(limit):
    h = Harness([reply(str(i), text="not final") for i in range(limit)], max_model_requests=limit)
    with pytest.raises(ModelRequestLimitError, match=f"max_model_requests={limit}"):
        await h.invoke()
    assert h.create.await_count == limit
    assert not h.scripts["main"]


@pytest.mark.parametrize("limit", [1, 2, 4])
@pytest.mark.asyncio
async def test_final_on_last_allowed_request_succeeds(limit):
    h = Harness(
        [
            *(reply(str(i), text="not final") for i in range(limit - 1)),
            reply("last", call("last")),
        ],
        max_model_requests=limit,
    )
    assert (await h.invoke()).output == {"value": 1}
    assert h.create.await_count == limit


@pytest.mark.parametrize("schema", [None, Result])
@pytest.mark.parametrize("mixed", [False, True])
@pytest.mark.asyncio
async def test_exhausted_budget_does_not_execute_ordinary_side_effects(schema, mixed):
    effects = []
    calls = [call("side_effect", "lookup")]
    if mixed:
        calls.append(call("final"))
    h = Harness(
        [reply("last", *calls)], tools={"lookup": ordinary_tool(effects)}, max_model_requests=1
    )
    with pytest.raises(ModelRequestLimitError):
        await h.invoke(schema)
    assert effects == []
    h.create.assert_awaited_once()


@pytest.mark.parametrize("limit", [0, -1, True, False, 1.0, 2.5, "2", None])
def test_invalid_request_limit_rejected_at_construction_before_any_hook_or_client(limit):
    client = Mock()
    with pytest.raises(ValueError, match="positive int"):
        LLMTextService(client=client, max_model_requests=limit)
    assert client.mock_calls == []


@pytest.mark.asyncio
async def test_default_budget_is_ten_and_mutated_invalid_budget_is_rechecked():
    h = Harness([])
    assert h.service.max_model_requests == 10
    h.service.max_model_requests = True
    with pytest.raises(ValueError, match="positive int"):
        await h.invoke()
    h.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_sequential_invocations_receive_independent_full_budgets():
    h = Harness(
        [
            reply("a1", text="retry"),
            reply("a2", call("a2")),
            reply("b1", text="retry"),
            reply("b2", call("b2")),
        ],
        max_model_requests=2,
    )
    first = await h.invoke()
    # A fresh invocation is not a continuation of the preceding history.
    h.previous.clear()
    second = await h.invoke()
    assert first.output == second.output == {"value": 1}
    assert h.create.await_count == 4
    assert len(h.requests["main"][2]["input"]) == 1


@pytest.mark.asyncio
async def test_parallel_invocations_share_service_but_not_request_budget_or_history():
    h = Harness(
        {
            key: [reply(f"{key}1", text="retry"), reply(f"{key}2", call(f"{key}2"))]
            for key in ("a", "b")
        },
        max_model_requests=2,
    )
    reached = {key: asyncio.Event() for key in ("a", "b")}
    original = h.provider

    async def interleaved(**payload):
        key = payload["input"][0]["content"]
        if not h.requests[key]:
            reached[key].set()
            await reached["b" if key == "a" else "a"].wait()
        return await original(**payload)

    h.create.side_effect = interleaved
    results = await asyncio.wait_for(
        asyncio.gather(
            *(h.invoke(messages=[{"role": "user", "content": key}]) for key in ("a", "b"))
        ),
        timeout=2,
    )
    assert [result.output for result in results] == [{"value": 1}, {"value": 1}]
    assert [len(h.requests[key]) for key in ("a", "b")] == [2, 2]


@pytest.mark.asyncio
async def test_output_uses_json_aliases_nested_dates_and_last_response_metadata():
    final_args = '{"nestedResult": {"eventDate": "2026-11-01"}, "labels": ["one"]}'
    h = Harness(
        [
            reply("retry", text="not final", tokens=100),
            reply("last", call("last", arguments=final_args), text="raw final", tokens=7),
        ]
    )
    result = await h.invoke(AliasedResult)
    assert result.output == {"nestedResult": {"eventDate": "2026-11-01"}, "labels": ["one"]}
    assert result.raw_text == h.parsed[-1].raw_text == "raw final"
    assert result.total_tokens == h.parsed[-1].total_tokens == 7
    assert result.messages[:-1] == h.parsed[-1].messages
    assert result.tool_calls == []
    assert h.parsed[-1].tool_calls[0].call_id == "last"


class HookRecorder(BaseAgentMiddleware):
    def __init__(self):
        self.events = []

    async def before_agent(self, service, messages):
        self.events.append("before_agent")
        return messages

    async def after_agent(self, service, response):
        self.events.append("after_agent")
        return response

    async def before_model(self, service, messages):
        self.events.append("before_model")
        return messages

    async def after_model(self, service, response):
        self.events.append("after_model")
        return response

    async def wrap_tool_call(self, service, tool_call, handler):
        self.events.append(f"tool:{tool_call.name}")
        return await handler(tool_call)


@pytest.mark.asyncio
async def test_hooks_agent_once_model_each_step_tools_only_ordinary():
    hooks = HookRecorder()
    effects = []
    h = Harness(
        [
            reply("mixed", call("ordinary", "lookup"), call("early")),
            reply("bad", call("bad", arguments="{}")),
            reply("ok", call("ok")),
        ],
        tools={"lookup": ordinary_tool(effects)},
        middlewares=[hooks],
    )
    await h.invoke()
    assert hooks.events == [
        "before_agent",
        "before_model",
        "after_model",
        "tool:lookup",
        "before_model",
        "after_model",
        "before_model",
        "after_model",
        "after_agent",
    ]
    assert effects == [1]
    assert LLMTextService._process_response is BaseLLMService._process_response


@pytest.mark.asyncio
async def test_final_bypasses_real_tool_limit_middleware(monkeypatch):
    # Load only this leaf: courses.agents.middlewares.__init__ imports unrelated
    # infrastructure. Restore the two exports on the runner's package stub after
    # the test; the middleware implementation itself is not mocked.
    import src.llm_service as package
    from src.llm_service.protocols import LLMTextServiceProtocol

    monkeypatch.setattr(package, "BaseAgentMiddleware", BaseAgentMiddleware, raising=False)
    monkeypatch.setattr(package, "LLMTextServiceProtocol", LLMTextServiceProtocol, raising=False)
    path = Path(__file__).resolve().parents[2] / "src/courses/agents/middlewares/tool_limit.py"
    spec = importlib.util.spec_from_file_location("isolated_actual_tool_limit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    limits = module.ToolCallLimitMiddleware({"lookup": 0, FINAL: 0})
    effects = []
    h = Harness(
        [reply("ordinary", call("ordinary", "lookup")), reply("final", call("final"))],
        tools={"lookup": ordinary_tool(effects)},
        middlewares=[limits],
    )
    assert (await h.invoke()).output == {"value": 1}
    assert effects == []
    assert "limit is exhausted" in outputs(h.requests["main"][1]["input"])["ordinary"]
    assert limits.tool_limits == {"lookup": 0, FINAL: 0}


@pytest.mark.parametrize("occupied_by", ["key", "tool_name", "both_suffixes"])
@pytest.mark.asyncio
async def test_final_name_avoids_both_mapping_keys_and_declared_names(occupied_by):
    effects = []
    if occupied_by == "key":
        tools = {FINAL: ordinary_tool(effects)}
    elif occupied_by == "tool_name":
        tools = {"different_key": ordinary_tool(effects, name=FINAL)}
    else:
        tools = {FINAL: ordinary_tool(effects, name=f"{FINAL}_1")}
    expected = f"{FINAL}_2" if occupied_by == "both_suffixes" else f"{FINAL}_1"
    h = Harness([reply("final", call("final", expected))], tools=tools)
    assert (await h.invoke()).output == {"value": 1}
    assert h.requests["main"][0]["tools"][-1]["name"] == expected
    assert h.service.tools == tools
    assert effects == []


@pytest.mark.parametrize("failure", ["auth", "config", "transport", "429", "incomplete"])
@pytest.mark.asyncio
async def test_model_errors_propagate_not_validation_feedback(failure):
    request = httpx.Request("POST", "https://provider.invalid/responses")
    if failure in {"auth", "429"}:
        error = openai.APIStatusError(
            "synthetic error",
            response=httpx.Response(401 if failure == "auth" else 429, request=request),
            body=None,
        )
    elif failure == "config":
        error = ValueError("synthetic configuration failure")
    elif failure == "transport":
        error = openai.APIConnectionError(request=request)
    else:
        error = reply("incomplete", status="incomplete")
    h = Harness([error, reply("must_not_be_used", call("unused"))])
    with pytest.raises(
        StructuredOutputError if failure == "incomplete" else type(error)
    ) as caught:
        await h.invoke()
    if failure != "incomplete":
        assert caught.value is error
    h.create.assert_awaited_once()
    assert len(h.scripts["main"]) == 1


@pytest.mark.parametrize("stage", ["model", "tool"])
@pytest.mark.asyncio
async def test_actual_task_cancellation_at_model_or_tool_is_not_swallowed(stage):
    entered = asyncio.Event()
    blocker = asyncio.Event()
    hooks = HookRecorder()
    effects = []

    async def block(*args, **kwargs):
        entered.set()
        await blocker.wait()

    h = Harness(
        [reply("ordinary", call("ordinary", "lookup")), reply("unused", call("unused"))],
        tools={"lookup": ordinary_tool(effects, action=block)},
        middlewares=[hooks],
    )
    if stage == "model":
        h.create.side_effect = block
    task = asyncio.create_task(h.invoke())
    try:
        await asyncio.wait_for(entered.wait(), timeout=2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    h.create.assert_awaited_once()
    assert "after_agent" not in hooks.events
    assert effects == ([1] if stage == "tool" else [])
    if stage == "model":
        assert "after_model" not in hooks.events


@pytest.mark.parametrize("text", ["", "plain", '{"value": 5}', "[1, 2]"])
@pytest.mark.asyncio
async def test_without_schema_text_semantics_are_unchanged(text):
    h = Harness([reply("text", text=text)], max_model_requests=1)
    result = await h.invoke(schema=None)
    assert result.output is None
    assert result.raw_text == (text or None)
    assert result.tool_calls == []
    assert "tools" not in h.requests["main"][0]
    h.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_without_schema_ordinary_tools_still_loop_then_return_text():
    effects = []
    h = Harness(
        [reply("tool", call("ordinary", "lookup")), reply("text", text="done")],
        tools={"lookup": ordinary_tool(effects)},
        max_model_requests=2,
    )
    result = await h.invoke(schema=None)
    assert effects == [1]
    assert result.raw_text == "done" and result.output is None
    assert all(t["name"] != FINAL for t in h.requests["main"][0]["tools"])


@pytest.mark.asyncio
async def test_base_send_request_transmits_internal_flag_and_real_dto_over_mock_http():
    response_body = LLMTextResponse(raw_text="plain", total_tokens=3).model_dump(mode="json")
    http_response = SimpleNamespace(json=AsyncMock(return_value=response_body))
    session = SimpleNamespace(post=AsyncMock(return_value=http_response))
    lifecycle = []

    @asynccontextmanager
    async def token_session():
        lifecycle.append("enter")
        try:
            yield session
        finally:
            lifecycle.append("exit")

    client = SimpleNamespace(_get_token_session=Mock(side_effect=token_session))
    service = LLMTextService(client=client, model="requested", reasoning="low", temperature=0.2)
    result = await service.invoke(copy.deepcopy(INPUT))
    assert result == LLMTextResponse.model_validate(response_body)
    session.post.assert_awaited_once_with(
        url="/api/v1/responses/text?model=requested",
        json={"messages": INPUT, "reasoning": "low", "temperature": 0.2, "disable_retries": True},
    )
    assert lifecycle == ["enter", "exit"]
    client._get_token_session.assert_called_once_with()


@pytest.mark.parametrize("schema", [None, Result])
@pytest.mark.asyncio
async def test_only_tools_before_last_request_may_have_side_effects(schema):
    effects = []
    h = Harness(
        [
            reply("first", call("allowed", "lookup", '{"value": 1}')),
            reply("last", call("forbidden", "lookup", '{"value": 2}')),
        ],
        tools={"lookup": ordinary_tool(effects)},
        max_model_requests=2,
    )
    with pytest.raises(ModelRequestLimitError):
        await h.invoke(schema)
    assert effects == [1]
    assert h.create.await_count == 2
    assert json.loads(outputs(h.requests["main"][1]["input"])["allowed"]) == {"seen": 1}


@pytest.mark.parametrize("parallel", [1, 2])
@pytest.mark.asyncio
async def test_ordinary_tool_concurrency_limit_does_not_spend_model_budget(parallel):
    active = 0
    peak = 0
    entered = asyncio.Event()
    release = asyncio.Event()
    effects = []

    async def action(value):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        if active == parallel:
            entered.set()
        try:
            await release.wait()
            return {"seen": value}
        finally:
            active -= 1

    h = Harness(
        [
            reply(
                "batch",
                *(call(f"ordinary{i}", "lookup", json.dumps({"value": i})) for i in range(4)),
            ),
            reply("final", call("final")),
        ],
        tools={"lookup": ordinary_tool(effects, action=action)},
        max_parallel=parallel,
        max_model_requests=2,
    )
    task = asyncio.create_task(h.invoke())
    try:
        await asyncio.wait_for(entered.wait(), timeout=2)
        assert active == peak == parallel
        assert h.create.await_count == 1
        release.set()
        result = await asyncio.wait_for(task, timeout=2)
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    assert sorted(effects) == [0, 1, 2, 3]
    assert peak == parallel and active == 0
    assert result.output == {"value": 1}
    assert h.create.await_count == 2
    assert len(outputs(h.requests["main"][1]["input"])) == 4


@pytest.mark.asyncio
async def test_without_schema_user_tool_named_like_final_remains_ordinary():
    effects = []
    h = Harness(
        [reply("ordinary", call("ordinary", FINAL)), reply("text", text="done")],
        tools={FINAL: ordinary_tool(effects, name=FINAL)},
    )
    result = await h.invoke(schema=None)
    assert effects == [1]
    assert result.raw_text == "done" and result.output is None
    assert json.loads(outputs(result.messages)["ordinary"]) == {"seen": 1}
    assert len(h.requests["main"][0]["tools"]) == 1


@pytest.mark.parametrize("failure", ["auth", "config", "transport"])
@pytest.mark.asyncio
async def test_internal_http_errors_propagate_without_feedback_or_extra_post(failure):
    request = httpx.Request("POST", "https://internal.invalid/responses")
    errors = {
        "auth": httpx.HTTPStatusError(
            "synthetic auth", request=request, response=httpx.Response(401, request=request)
        ),
        "config": ValueError("synthetic client configuration"),
        "transport": httpx.ConnectError("synthetic transport", request=request),
    }
    error = errors[failure]
    session = SimpleNamespace(post=AsyncMock(side_effect=error))
    exited = []

    @asynccontextmanager
    async def token_session():
        try:
            yield session
        finally:
            exited.append(True)

    service = LLMTextService(client=SimpleNamespace(_get_token_session=token_session))
    with pytest.raises(type(error)) as caught:
        await service.invoke(copy.deepcopy(INPUT), schema=Result)
    assert caught.value is error
    session.post.assert_awaited_once()
    assert exited == [True]


@pytest.mark.parametrize("kind", ["invalid_final", "multiple_finals"])
@pytest.mark.asyncio
async def test_last_request_cannot_retry_invalid_or_multiple_final_calls(kind):
    calls = [call("bad", arguments="{}")]
    if kind == "multiple_finals":
        calls = [call("one"), call("two")]
    h = Harness([reply("last", *calls)], max_model_requests=1)
    with pytest.raises(ModelRequestLimitError):
        await h.invoke()
    h.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_multiple_ordinary_tools_each_have_output_before_a_separate_final():
    effects = []
    h = Harness(
        [
            reply(
                "mixed",
                call("one", "lookup", '{"value": 1}'),
                call("two", "lookup", '{"value": 2}'),
                call("early1"),
                call("early2"),
            ),
            reply("final", call("final")),
        ],
        tools={"lookup": ordinary_tool(effects)},
    )
    await h.invoke()
    assert sorted(effects) == [1, 2]
    feedback = outputs(h.requests["main"][1]["input"])
    assert set(feedback) == {"one", "two", "early1", "early2"}
    assert json.loads(feedback["one"]) == {"seen": 1}
    assert json.loads(feedback["two"]) == {"seen": 2}
    assert all("error" in json.loads(feedback[key]) for key in ("early1", "early2"))


@pytest.mark.asyncio
async def test_schema_feedback_does_not_disclose_validator_input_or_context():
    class SensitiveResult(BaseModel):
        value: int

        @field_validator("value")
        @classmethod
        def reject_synthetic_secret(cls, value):
            if value == 123456:
                raise ValueError("SYNTHETIC_PRIVATE_VALIDATOR_MESSAGE")
            return value

    h = Harness(
        [reply("bad", call("bad", arguments='{"value": 123456}')), reply("ok", call("ok"))]
    )
    await h.invoke(SensitiveResult)
    feedback = outputs(h.requests["main"][1]["input"])["bad"]
    assert "value_error" in feedback
    assert "123456" not in feedback
    assert "SYNTHETIC_PRIVATE" not in feedback
