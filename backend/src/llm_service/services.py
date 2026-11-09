# pyright: reportOptionalSubscript=false, reportArgumentType=false, reportGeneralTypeIssues=false, reportOptionalIterable=false
from typing import Any, Literal

import logging
from abc import ABC, abstractmethod
from asyncio import Semaphore, gather
from collections.abc import Awaitable, Callable, Sequence
from copy import deepcopy
from functools import wraps

import aiohttp
from openai.types.responses import ToolParam
from pydantic import BaseModel, ValidationError

from src.shared.infra.services import SrvBaseClient

from .dataclasses import StructuredTool
from .middleware import BaseAgentMiddleware
from .protocols import LLMServiceProtocol
from .schemas import (
    LLMImageRequest,
    LLMImageResponse,
    LLMTextRequest,
    LLMTextResponse,
    Runtime,
    ToolCallParsed,
)
from .strict_schema import to_strict_json_schema

logger = logging.getLogger(__name__)


class ModelRequestLimitError(ValueError):
    """The invocation cannot complete within its model request budget."""


def execute_once_per_loop[ResponseT: BaseModel](
    func: Callable[..., Awaitable[ResponseT]],
) -> Callable[..., Awaitable[ResponseT]]:

    @wraps(func)
    async def wrapper(
        self: LLMServiceProtocol,
        messages: list[dict[str, Any]] | str,
        *args,
        **kwargs,
    ) -> ResponseT:
        for middleware in self.middlewares:
            messages = await middleware.before_agent(self, messages)
        response = await func(self, messages, *args, **kwargs)
        for middleware in self.middlewares:
            response = await middleware.after_agent(self, response)
        return response

    return wrapper


def execute_each_invoke[ResponseT: BaseModel](
    func: Callable[..., Awaitable[ResponseT]],
) -> Callable[..., Awaitable[ResponseT]]:
    @wraps(func)
    async def wrapper(
        self: LLMServiceProtocol,
        messages: list[dict[str, Any]] | str,
        *args,
        **kwargs,
    ) -> ResponseT:
        for middleware in self.middlewares:
            messages = await middleware.before_model(self, messages)
        result = await func(self, messages, *args, **kwargs)
        for mw in self.middlewares:
            result = await mw.after_model(self, result)
        return await self._process_response(result, *args, **kwargs)

    return wrapper


class BaseLLMService[RequestT: BaseModel, ResponseT: BaseModel](ABC):
    response_model: type[ResponseT]

    def __init__(
        self,
        client: SrvBaseClient,
        middlewares: Sequence[BaseAgentMiddleware] | None = None,
        runtime: Runtime | None = None,
    ) -> None:
        self._client = client
        self.middlewares = middlewares if middlewares is not None else []
        self.runtime = runtime
        self.request_timeout: float | None = None

    async def _send_request(self, request: RequestT, path: str) -> ResponseT:
        async with self._client._get_token_session() as session:  # noqa: SLF001
            kwargs = {}
            if self.request_timeout is not None:
                kwargs["timeout"] = aiohttp.ClientTimeout(total=self.request_timeout)
            response = await session.post(
                url=path, json=request.model_dump(exclude_none=True), **kwargs
            )

            return self.response_model.model_validate(await response.json())

    @abstractmethod
    async def _run_loop(self, *args, **kwargs) -> ResponseT: ...

    async def _process_response(self, response: ResponseT, *args, **kwargs) -> ResponseT:
        return response


class LLMTextService(BaseLLMService[LLMTextRequest, LLMTextResponse]):
    response_model = LLMTextResponse

    def __init__(
        self,
        client: SrvBaseClient,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: dict[str, StructuredTool] | None = None,
        middlewares: Sequence[BaseAgentMiddleware] | None = None,
        reasoning: Literal["low", "medium", "high"] | None = None,
        temperature: float | None = None,
        runtime: Runtime | None = None,
        max_parallel: int = 4,
        max_model_requests: int = 10,
        request_timeout: float | None = None,
    ) -> None:
        self._validate_request_limit(max_model_requests)
        super().__init__(client=client, runtime=runtime, middlewares=middlewares)
        self.model = model
        self.system_prompt = system_prompt
        self.tools = tools
        self.reasoning: Literal["low", "medium", "high"] | None = reasoning
        self.temperature = temperature
        self.semaphore = Semaphore(max_parallel)
        self.max_model_requests = max_model_requests
        self.request_timeout = request_timeout

    @staticmethod
    def _validate_request_limit(value: int) -> None:
        if type(value) is not int or value <= 0:
            raise ValueError("max_model_requests must be a positive int")

    @execute_once_per_loop
    async def invoke(
        self,
        messages: list[dict[str, Any]],
        schema: type[BaseModel] | None = None,
    ) -> LLMTextResponse:
        limit = self.max_model_requests
        tools = [tool.to_tool_params() for tool in (self.tools or {}).values()]
        final_name = None
        instructions = self.system_prompt
        if schema is not None:
            final_name = self._final_tool_name()
            tools.append(
                {
                    "type": "function",
                    "name": final_name,
                    "description": "Submit the final structured result and finish the task.",
                    "parameters": to_strict_json_schema(schema),
                    "strict": True,
                }
            )
            instructions = "\n\n".join(
                filter(
                    None,
                    [
                        instructions,
                        f"Finish by calling {final_name} exactly once, on its own, after "
                        "receiving all other tool results. Its arguments must match the schema.",
                    ],
                )
            )

        # Each internal POST is reserved before sending. This path disables router
        # and SDK retries, so it can initiate at most one provider attempt.
        for attempt in range(limit):
            response = await self._run_loop(
                messages=messages,
                tools=tools or None,
                instructions=instructions,
                final_tool_name=final_name,
            )
            final_calls = [t for t in response.tool_calls if t.name == final_name]
            ordinary_calls = [t for t in response.tool_calls if t.name != final_name]
            feedback = []
            if len(final_calls) == 1 and not ordinary_calls:
                output, error = self._validate_final(final_calls[0], schema)
                if error is None:
                    response.output = output
                    response.messages = [
                        *response.messages,
                        StructuredTool.to_tool_result(
                            final_calls[0].call_id,
                            "Final result accepted.",
                        ),
                    ]
                    response.tool_calls = []
                    return response
                feedback.append(
                    StructuredTool.to_tool_result(
                        final_calls[0].call_id,
                        {"error": error},
                    )
                )
            elif final_calls:
                error = (
                    "Multiple final calls are not allowed. Submit exactly one final call."
                    if len(final_calls) > 1
                    else "Do not submit the final result together with other tools. "
                    "Wait for their results, then submit one separate final call."
                )
                feedback.extend(
                    StructuredTool.to_tool_result(t.call_id, {"error": error}) for t in final_calls
                )
            elif not ordinary_calls and schema is None:
                return response

            # Every remaining branch needs another model request. Do not execute
            # ordinary tools with side effects if that request is already forbidden.
            if attempt + 1 == limit:
                raise ModelRequestLimitError(
                    f"LLM invocation exhausted max_model_requests={limit} without a final result"
                )
            if ordinary_calls:
                handler = self._build_tool_call_handler()
                feedback.extend(await gather(*(handler(tool) for tool in ordinary_calls)))
            elif not final_calls:
                feedback.append(
                    {
                        "role": "user",
                        "content": f"Submit the result by calling {final_name}; "
                        "a text response does not complete this task.",
                    }
                )
            messages = response.messages + feedback

        raise ModelRequestLimitError("LLM model request budget exhausted")

    def _final_tool_name(self) -> str:
        occupied = set(self.tools or {}) | {tool.name for tool in (self.tools or {}).values()}
        name = "submit_final_result"
        suffix = 1
        while name in occupied:
            name = f"submit_final_result_{suffix}"
            suffix += 1
        return name

    @staticmethod
    def _validate_final(
        tool: ToolCallParsed,
        schema: type[BaseModel],
    ) -> tuple[dict[str, Any] | None, str | None]:
        if tool.arguments_error is not None:
            return None, tool.arguments_error + ". Correct the arguments and call again."
        try:
            schema.model_validate(deepcopy(tool.arguments))
        except ValidationError as exc:
            # Custom validator messages/context may contain sensitive input values.
            errors = exc.errors(include_input=False, include_context=False, include_url=False)
            details = "; ".join(f"{e['loc']}: {e['type']}" for e in errors)
            return None, f"Final result failed schema validation: {details}. Correct and retry."
        # Preserve the input JSON shape (including validation aliases), as the
        # router did previously. Consumers validate this dict again; a model dump
        # could replace validation aliases with incompatible serialization aliases.
        return tool.arguments, None

    @execute_each_invoke
    async def _run_loop(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolParam] | None = None,
        instructions: str | None = None,
        final_tool_name: str | None = None,
    ) -> LLMTextResponse:
        request = LLMTextRequest(
            input=messages,
            tools=tools,
            instructions=instructions,
            disable_retries=True,
            final_tool_name=final_tool_name,
            reasoning=self.reasoning,
            temperature=self.temperature,
            request_timeout=self.request_timeout,
        )

        if self.runtime is not None:
            self.runtime.messages = list(messages)

        return await self._send_request(
            request=request,
            path=f"/api/v1/responses/text{f'?model={self.model}' if self.model is not None else ''}",  # noqa: E501
        )
        # return await self._send_request(
        #     request=request,
        #     path="/api/v1/responses/text?model=gpt-5-nano",
        # )

    def _build_tool_call_handler(self) -> Callable[[ToolCallParsed], Awaitable[dict]]:
        async def base_handler(tool: ToolCallParsed) -> dict:

            return await self._process_tool(tool)

        handler: Callable[[ToolCallParsed], Awaitable[dict]] = base_handler
        for middleware in reversed(self.middlewares):
            handler = self._wrap_with(middleware, handler)
        return handler

    def _wrap_with(
        self,
        middleware: BaseAgentMiddleware,
        next_handler: Callable[[ToolCallParsed], Awaitable[dict]],
    ) -> Callable[[ToolCallParsed], Awaitable[dict]]:

        async def wrapped(tool: ToolCallParsed) -> dict:

            return await middleware.wrap_tool_call(self, tool, next_handler)

        return wrapped

    async def _process_tool(self, tool: ToolCallParsed) -> dict:

        logger.info("tool call %s", tool.name)
        callable_func = (self.tools or {}).get(tool.name)
        if callable_func is None:
            logger.warning(
                "Unknown tool requested: name=%s, call_id=%s",
                tool.name,
                tool.call_id,
            )
            return StructuredTool.to_tool_result(
                call_id=tool.call_id,
                result={"error": f"Unknown tool '{tool.name}'. Use only available tools."},
            )
        async with self.semaphore:
            try:
                result = await callable_func.run_tool(
                    raw_args=tool.arguments, runtime=self.runtime
                )
                return callable_func.to_tool_result(call_id=tool.call_id, result=result)

            except Exception:
                logger.exception("tool call %s failed", tool.name)
                return callable_func.to_tool_result(
                    call_id=tool.call_id,
                    result={
                        "error": f"Tool '{tool.name}' failed to execute due to an internal error"
                    },
                )


class LLMImageService(BaseLLMService[LLMImageRequest, LLMImageResponse]):
    response_model = LLMImageResponse

    def __init__(
        self,
        client: SrvBaseClient,
        model: str | None = None,
        middlewares: Sequence[BaseAgentMiddleware] | None = None,
        runtime: Runtime | None = None,
    ) -> None:
        super().__init__(client=client, runtime=runtime, middlewares=middlewares)
        self.model = model

    @execute_once_per_loop
    async def invoke(
        self,
        messages: str,
        images: list[str] | None = None,
    ) -> LLMImageResponse:
        return await self._run_loop(messages=messages, images=images)

    @execute_each_invoke
    async def _run_loop(
        self,
        messages: str,
        images: list[str] | None = None,
    ) -> LLMImageResponse:
        request = LLMImageRequest(image=images, prompt=str(messages))
        if self.runtime is not None:
            self.runtime.messages = messages
        return await self._send_request(
            request=request,
            path=f"/api/v1/responses/image{f'?model={self.model}' if self.model is not None else ''}",  # noqa: E501
        )
        # return await self._send_request(
        #     request=request,
        #     path="/api/v1/responses/image?model=gpt-image-2",
        # )
