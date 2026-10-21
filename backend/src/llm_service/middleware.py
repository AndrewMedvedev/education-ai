from __future__ import annotations

from typing import Any

from abc import ABC
from collections.abc import Awaitable, Callable

from .protocols import (
    LLMServiceProtocol,
    LLMTextServiceProtocol,
    ResponseT,
)
from .schemas import ToolCallParsed

Messages = list[dict[str, Any]] | str


class BaseAgentMiddleware(ABC):  # noqa: B024
    """
    Базовый класс миддлвари для LLMService.
    Переопределяйте только нужные хуки — остальные по умолчанию
    просто пропускают данные дальше без изменений (pass-through).
    """

    # --- срабатывает РОВНО ОДИН РАЗ за весь запуск invoke() ---
    async def before_agent(
        self,
        service: LLMServiceProtocol,
        messages: Messages,
    ) -> Messages:
        return messages

    async def after_agent(
        self,
        service: LLMServiceProtocol,  # noqa: ARG002
        response: ResponseT,
    ) -> ResponseT:
        return response

    # --- срабатывает перед/после КАЖДОГО вызова модели ---
    async def before_model(
        self,
        service: LLMServiceProtocol,  # noqa: ARG002
        messages: Messages,
    ) -> Messages:
        return messages

    async def after_model(
        self,
        service: LLMServiceProtocol,  # noqa: ARG002
        response: ResponseT,
    ) -> ResponseT:
        return response

    # --- оборачивает КАЖДЫЙ вызов инструмента ---
    async def wrap_tool_call(
        self,
        service: LLMTextServiceProtocol,  # noqa: ARG002
        tool: ToolCallParsed,
        handler: Callable[[ToolCallParsed], Awaitable[dict]],
    ) -> dict:
        # по умолчанию просто вызываем следующий слой цепочки
        return await handler(tool)
