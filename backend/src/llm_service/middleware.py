# ruff: file-ignore[abstract-base-class-without-abstract-method, no-self-use, unused-method-argument]

from __future__ import annotations

from typing import Any

from abc import ABC
from collections.abc import Awaitable, Callable

from .schemas import (
    LLMServiceProtocol,
    LLMTextServiceProtocol,
    ResponseT,
    ToolCallParsed,
)

Messages = list[dict[str, Any]] | str


class BaseAgentMiddleware(ABC):
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
        """Выполняет шаг middleware `before_agent`, чтобы расширить поведение агента без изменения сервиса."""
        return messages

    async def after_agent(
        self,
        service: LLMServiceProtocol,
        response: ResponseT,
    ) -> ResponseT:
        """Выполняет шаг middleware `after_agent`, чтобы расширить поведение агента без изменения сервиса."""
        return response

    # --- срабатывает перед/после КАЖДОГО вызова модели ---
    async def before_model(
        self,
        service: LLMServiceProtocol,
        messages: Messages,
    ) -> Messages:
        """Выполняет шаг middleware `before_model`, чтобы расширить поведение агента без изменения сервиса."""
        return messages

    async def after_model(
        self,
        service: LLMServiceProtocol,
        response: ResponseT,
    ) -> ResponseT:
        """Выполняет шаг middleware `after_model`, чтобы расширить поведение агента без изменения сервиса."""
        return response

    # --- оборачивает КАЖДЫЙ вызов инструмента ---
    async def wrap_tool_call(
        self,
        service: LLMTextServiceProtocol,
        tool: ToolCallParsed,
        handler: Callable[[ToolCallParsed], Awaitable[dict]],
    ) -> dict:
        # по умолчанию просто вызываем следующий слой цепочки
        """Выполняет шаг middleware `wrap_tool_call`, чтобы расширить поведение агента без изменения сервиса."""
        return await handler(tool)
