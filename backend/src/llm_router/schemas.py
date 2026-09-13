from typing import Any, Protocol

from collections.abc import Awaitable, Callable

from pydantic import BaseModel, Field

from src.shared.application.dtos import Page


class AIModelSchema(BaseModel):
    name: str = Field(description="Имя модели")
    description: str = Field(description=" Точное описание модели")
    context: int = Field(description="контекст модели")


class CacheAIModelsProtocol(Protocol):
    async def __call__(
        self,
        func: Callable[..., Awaitable[Any]],
        ttl: int = 300,
        key: str = "ai_models",
        lock_timeout: int = 30,
        *args: Any,
        **kwargs: Any,
    ) -> Page:
        """Описывает вызываемый кэширующий обработчик списка AI-моделей."""
        ...
