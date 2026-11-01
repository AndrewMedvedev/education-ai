"""Exercise the real router/parser boundary with an offline Responses provider."""

import asyncio
import math
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import openai
import pytest
from openai.types.responses import Response, ResponseFunctionToolCall, ResponseReasoningItem
from pydantic import ValidationError

from src.llm_router import services
from src.llm_router.domain.vo import LLMInvocationStatus
from src.llm_router.services import LLMTextRouter
from src.llm_router.utils import StructuredOutputError, parse_llm_response
from src.llm_service.schemas import LLMTextRequest

HISTORY = [
    {"role": "user", "content": "synthetic question"},
    {"type": "function_call", "call_id": "previous", "name": "lookup", "arguments": "{}"},
    {"type": "function_call_output", "call_id": "previous", "output": "ok"},
]
TOOL = {
    "type": "function",
    "name": "lookup",
    "description": "Synthetic lookup",
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    "strict": True,
}


def response(*items, status="completed", error=None, text=""):
    # model_construct permits deliberately invalid provider arguments (including
    # None) without a test-side SDK validation hiding the parser's behavior.
    result = Response.model_construct(
        output=list(items),
        status=status,
        error=error,
        usage=None,
        incomplete_details=SimpleNamespace(reason="max_output_tokens"),
    )
    if text:
        from openai.types.responses import ResponseOutputMessage, ResponseOutputText

        result.output.append(
            ResponseOutputMessage.model_construct(
                id="msg_test",
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
    return result


def tool_response(arguments):
    return response(
        ResponseReasoningItem.model_construct(
            id="rs_test",
            type="reasoning",
            summary=[],
            encrypted_content="synthetic-reasoning",
        ),
        ResponseFunctionToolCall.model_construct(
            id="fc_test",
            type="function_call",
            call_id="call_test",
            name="lookup",
            arguments=arguments,
            status="completed",
        ),
    )


def make_router(result=None, error=None):
    create = AsyncMock(return_value=result, side_effect=error)
    bounded_create = AsyncMock(return_value=result, side_effect=error)
    client = SimpleNamespace(
        responses=SimpleNamespace(create=create),
        with_options=Mock(
            return_value=SimpleNamespace(
                responses=SimpleNamespace(create=bounded_create),
            )
        ),
    )
    publisher = SimpleNamespace(publish=AsyncMock())
    router = LLMTextRouter(
        ai_model_repos=Mock(),
        event_publisher=publisher,
        client=client,
        wrapper=AsyncMock(),
    )
    return router, client, publisher


@pytest.fixture
def retry_sleep(monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr(services.LLMRouter._invoke_with_retries.retry, "sleep", sleep)
    return sleep


@pytest.mark.parametrize(
    "arguments,invalid",
    [
        ('{"value": 7}', False),
        ("{}", False),
        ('{"value":', True),
        ("not json", True),
        ("", True),
        (None, True),
        ("null", True),
        ("[]", True),
        ('"text"', True),
        ("42", True),
        ("true", True),
        ("NaN", True),
        ("Infinity", True),
        ("-Infinity", True),
        ('{"nested": [NaN]}', True),
        ('{"nested": {"value": Infinity}}', True),
        ('{"nested": [-Infinity]}', True),
    ],
)
@pytest.mark.parametrize("bounded", [True, None])
@pytest.mark.asyncio
async def test_tool_arguments_and_history_survive_router(arguments, invalid, bounded, retry_sleep):
    provider_response = tool_response(arguments)
    router, client, publisher = make_router(provider_response)
    schema = LLMTextRequest(
        input=HISTORY,
        tools=[TOOL],
        disable_retries=bounded,
        final_tool_name="lookup",
    )
    result = await router.call_llm(schema, model="requested-model-is-currently-ignored")

    tool = result.tool_calls[0]
    assert tool.call_id == "call_test"
    assert tool.name == "lookup"
    assert tool.arguments == ({"value": 7} if arguments == '{"value": 7}' else {})
    assert (tool.arguments_error is not None) is invalid
    if invalid:
        assert tool.arguments_error
    assert result.messages == HISTORY + [
        item.model_dump(mode="json", exclude_none=True, exclude_unset=True)
        for item in provider_response.output
    ]
    assert result.messages[-2]["encrypted_content"] == "synthetic-reasoning"
    assert result.messages[-1]["call_id"] == "call_test"
    assert schema.messages == HISTORY  # parser must not append into caller input
    assert result.output is None
    assert result.total_tokens == 0
    create = (
        client.with_options.return_value.responses.create if bounded else client.responses.create
    )
    create.assert_awaited_once_with(model="deepseek-v4-pro", input=HISTORY, tools=[TOOL])
    assert "final_tool_name" not in create.await_args.kwargs
    assert "disable_retries" not in create.await_args.kwargs
    if bounded:
        client.with_options.assert_called_once_with(max_retries=0)
        client.responses.create.assert_not_awaited()
    else:
        client.with_options.assert_not_called()
    retry_sleep.assert_not_awaited()
    event = publisher.publish.await_args.args[0]
    assert event.status == LLMInvocationStatus.COMPLETED
    assert event.response["tool_calls"][0]["call_id"] == "call_test"


def status_error(status):
    return openai.APIStatusError(
        "synthetic provider failure",
        response=httpx.Response(
            status, request=httpx.Request("POST", "https://provider.invalid/responses")
        ),
        body=None,
    )


@pytest.mark.parametrize(
    "failure",
    [
        "generic",
        "connection",
        "429",
        "500",
        "502",
        "503",
        "504",
        "incomplete",
        "parser",
        "response_error",
    ],
)
@pytest.mark.asyncio
async def test_bounded_failure_never_retries(failure, retry_sleep):
    result = response(text="ok")
    error = None
    expected = Exception
    if failure.isdigit():
        error = status_error(int(failure))
    elif failure == "generic":
        error = RuntimeError("synthetic failure")
    elif failure == "connection":
        error = openai.APIConnectionError(
            request=httpx.Request("POST", "https://provider.invalid")
        )
    elif failure == "incomplete":
        result = response(status="incomplete", text='{"ok": true}')
        expected = StructuredOutputError
    elif failure == "parser":
        result = response(text="not a JSON object")
        expected = StructuredOutputError
    else:
        result = response(error="synthetic response error")
        expected = ValueError
    router, client, publisher = make_router(result, error)
    schema = LLMTextRequest(input=HISTORY, disable_retries=True)
    if failure in {"incomplete", "parser"}:
        schema.text = {"format": {"type": "json_schema"}}
    with pytest.raises(expected) as caught:
        await router.call_llm(schema)
    if error is not None:
        assert caught.value is error
    client.with_options.assert_called_once_with(max_retries=0)
    client.with_options.return_value.responses.create.assert_awaited_once()
    payload = client.with_options.return_value.responses.create.await_args.kwargs
    assert "final_tool_name" not in payload
    assert "disable_retries" not in payload
    client.responses.create.assert_not_awaited()
    retry_sleep.assert_not_awaited()
    assert publisher.publish.await_count == 1
    assert publisher.publish.await_args.args[0].status == LLMInvocationStatus.FAILED


@pytest.mark.parametrize("flag", [None, False])
@pytest.mark.parametrize(
    "failure,attempts",
    [("generic", 3), ("429", 4), ("503", 4), ("parser", 3), ("incomplete", 3), ("400", 1)],
)
@pytest.mark.asyncio
async def test_default_consumers_keep_retry_budget(flag, failure, attempts, retry_sleep):
    error = status_error(int(failure)) if failure.isdigit() else RuntimeError("synthetic failure")
    result = response(
        text="not JSON", status="incomplete" if failure == "incomplete" else "completed"
    )
    if failure in {"parser", "incomplete"}:
        error = None
    router, client, publisher = make_router(result, error)
    schema = LLMTextRequest(input=HISTORY, disable_retries=flag)
    if error is None:
        schema.text = {"format": {"type": "json_schema"}}
    with pytest.raises(Exception) as caught:
        await router.call_llm(schema)
    if error is not None:
        assert caught.value is error
    else:
        assert isinstance(caught.value, StructuredOutputError)
    assert client.responses.create.await_count == attempts
    assert retry_sleep.await_count == attempts - 1
    client.with_options.assert_not_called()
    assert publisher.publish.await_count == attempts
    for call in client.responses.create.await_args_list:
        assert "disable_retries" not in call.kwargs
        assert "final_tool_name" not in call.kwargs


@pytest.mark.parametrize("flag", [None, False])
@pytest.mark.asyncio
async def test_default_retry_recovers_with_real_parser(flag, retry_sleep):
    router, client, publisher = make_router()
    client.responses.create.side_effect = [status_error(429), response(text="recovered")]
    result = await router.call_llm(LLMTextRequest(input=HISTORY, disable_retries=flag))
    assert result.raw_text == "recovered"
    assert client.responses.create.await_count == 2
    for provider_call in client.responses.create.await_args_list:
        assert "final_tool_name" not in provider_call.kwargs
        assert "disable_retries" not in provider_call.kwargs
    retry_sleep.assert_awaited_once()
    assert [call.args[0].status for call in publisher.publish.await_args_list] == [
        LLMInvocationStatus.FAILED,
        LLMInvocationStatus.COMPLETED,
    ]


@pytest.mark.parametrize("flag", [True, None, False])
@pytest.mark.asyncio
async def test_cancel_propagates_without_retry(flag, retry_sleep):
    cancellation = asyncio.CancelledError("synthetic cancellation")
    router, client, publisher = make_router(error=cancellation)
    with pytest.raises(asyncio.CancelledError) as caught:
        await router.call_llm(LLMTextRequest(input=HISTORY, disable_retries=flag))
    assert caught.value is cancellation
    create = client.with_options.return_value.responses.create if flag else client.responses.create
    create.assert_awaited_once()
    assert "final_tool_name" not in create.await_args.kwargs
    assert "disable_retries" not in create.await_args.kwargs
    retry_sleep.assert_not_awaited()
    publisher.publish.assert_not_awaited()


@pytest.mark.parametrize("arguments", ["null", "[]", "[1]", '"text"', "42", "true"])
@pytest.mark.parametrize("final_name", [None, "some_other_final"])
@pytest.mark.asyncio
async def test_ordinary_nonobject_keeps_dto_validation_error(arguments, final_name, retry_sleep):
    router, client, publisher = make_router(tool_response(arguments))
    schema = LLMTextRequest(
        input=HISTORY, tools=[TOOL], disable_retries=True, final_tool_name=final_name
    )
    with pytest.raises(ValidationError) as caught:
        await router.call_llm(schema)
    assert caught.value.errors()[0]["loc"] == ("arguments",)
    assert caught.value.errors()[0]["type"] == "dict_type"
    create = client.with_options.return_value.responses.create
    create.assert_awaited_once_with(model="deepseek-v4-pro", input=HISTORY, tools=[TOOL])
    assert "final_tool_name" not in create.await_args.kwargs
    retry_sleep.assert_not_awaited()
    assert publisher.publish.await_args.args[0].status == LLMInvocationStatus.FAILED


@pytest.mark.parametrize("arguments", ['{"value":', "not json", "", None])
@pytest.mark.parametrize("final_name", [None, "some_other_final"])
@pytest.mark.asyncio
async def test_ordinary_malformed_json_keeps_empty_dict_fallback(
    arguments, final_name, retry_sleep
):
    provider_response = tool_response(arguments)
    router, client, publisher = make_router(provider_response)
    result = await router.call_llm(
        LLMTextRequest(
            input=HISTORY,
            tools=[TOOL],
            disable_retries=True,
            final_tool_name=final_name,
        )
    )
    parsed = result.tool_calls[0]
    assert parsed.arguments == {}
    assert parsed.arguments_error
    assert parsed.call_id == "call_test"
    assert result.messages == HISTORY + [
        item.model_dump(mode="json", exclude_none=True, exclude_unset=True)
        for item in provider_response.output
    ]
    create = client.with_options.return_value.responses.create
    create.assert_awaited_once_with(model="deepseek-v4-pro", input=HISTORY, tools=[TOOL])
    assert "final_tool_name" not in create.await_args.kwargs
    retry_sleep.assert_not_awaited()
    assert publisher.publish.await_args.args[0].status == LLMInvocationStatus.COMPLETED


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
@pytest.mark.parametrize("final_name", [None, "some_other_final"])
@pytest.mark.asyncio
async def test_nonstandard_constant_rejection_is_scoped_to_matching_final(constant, final_name):
    router, client, _ = make_router(tool_response('{"nested": [' + constant + "]}"))
    result = await router.call_llm(
        LLMTextRequest(
            input=HISTORY,
            tools=[TOOL],
            disable_retries=True,
            final_tool_name=final_name,
        )
    )
    parsed = result.tool_calls[0]
    assert parsed.arguments_error is None
    value = parsed.arguments["nested"][0]
    if constant == "NaN":
        assert math.isnan(value)
    else:
        assert math.isinf(value)
        assert (value < 0) is constant.startswith("-")
    client.with_options.return_value.responses.create.assert_awaited_once_with(
        model="deepseek-v4-pro",
        input=HISTORY,
        tools=[TOOL],
    )


def test_runner_keeps_tested_modules_real_and_imports_service():
    from src.llm_router import decorators
    from src.llm_service import dataclasses, tools
    from src.llm_service import services as text_services

    for module in (services, decorators, dataclasses, text_services, tools):
        assert module.__file__
    assert parse_llm_response.__module__ == "src.llm_router.utils"
    assert not getattr(sys.modules["src"], "__file__", None)
    assert not getattr(sys.modules["src.core.settings"], "__file__", None)
    assert not getattr(sys.modules["src.core.providers"], "__file__", None)
