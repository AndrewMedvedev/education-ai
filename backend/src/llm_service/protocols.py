from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Protocol, TypeVar

from src.shared.infra.services.client import SrvBaseClient

if TYPE_CHECKING:
    from .middleware import BaseAgentMiddleware
from asyncio import Semaphore
from collections.abc import Sequence

from pydantic import BaseModel

from .dataclasses import StructuredTool
from .schemas import LLMTextResponse, Runtime, ToolCallParsed

RequestT = TypeVar("RequestT", bound=BaseModel)
ResponseT = TypeVar("ResponseT", bound=BaseModel)


class LLMServiceProtocol(Protocol[RequestT, ResponseT]):  # pyright: ignore[reportInvalidTypeVarUse]
    base_url: str
    response_model: type[ResponseT]
    _client: SrvBaseClient
    runtime: Runtime | None
    middlewares: Sequence[BaseAgentMiddleware] | None
    timeout: int

    async def _send_request(self, request: RequestT, path: str) -> ResponseT:
        """Описывает отправку HTTP-запроса к LLM-провайдеру."""
        ...

    async def _run_loop(self, *args, **kwargs) -> ResponseT:
        """Описывает основной цикл обращения к модели и обработки ответа."""
        ...

    async def _process_response(self, response: ResponseT, *args, **kwargs) -> ResponseT:
        """Описывает финальную обработку ответа перед возвратом результата."""
        ...


class LLMTextServiceProtocol(LLMServiceProtocol):
    system_prompt: str | None
    tools: dict[str, StructuredTool] | None
    reasoning: Literal["low", "medium", "high"] | None
    temperature: float | None
    semaphore: Semaphore

    async def _process_tool(self, tool: ToolCallParsed) -> dict:
        """Описывает выполнение tool-call и преобразование результата для LLM."""
        ...

    async def _process_response(
        self,
        response: LLMTextResponse,
        messages: list[dict[str, Any]],
        schema: type[BaseModel] | None = None,
    ) -> LLMTextResponse:
        """Обрабатывает ответ модели и продолжает tool-loop при необходимости."""
        ...


class LLMImageServiceProtocol(LLMServiceProtocol): ...
