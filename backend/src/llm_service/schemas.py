# ruff: file-ignore[unnecessary-placeholder]

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Protocol, TypeVar

from aiohttp import ClientSession

if TYPE_CHECKING:
    from .middleware import BaseAgentMiddleware
from asyncio import Semaphore
from collections.abc import Sequence

from openai.types.responses import ToolParam
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .dataclasses import StructuredTool
from .strict_schema import to_strict_json_schema


class ToolCallParsed(BaseModel):
    call_id: str
    name: str
    arguments: dict[str, Any]


class LLMTextRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    messages: list[dict[str, Any]] = Field(alias="input")
    tools: list[ToolParam] | None = None
    instructions: str | None = None
    reasoning: Literal["low", "medium", "high"] | None = None
    temperature: float | None = None
    text: dict[str, Any] | None = None

    def format_schema(self, schema: type[BaseModel]) -> None:
        """Форматирует схему данных, чтобы привести данные к ожидаемому виду."""
        self.text = {
            "format": {
                "type": "json_schema",
                "name": schema.__name__,
                "schema": to_strict_json_schema(TypeAdapter(schema)),
                "strict": True,
            }
        }


class LLMImageRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    image: list[str] | None = Field(default=None, min_length=1, max_length=5)
    messages: str = Field(alias="prompt")
    quality: Literal["standard", "hd", "low", "medium", "high", "auto"] = "medium"
    size: Literal["1024x1024", "1024x1536", "1536x1024"] = "1024x1024"
    output_format: str = "png"


class LLMTextResponse(BaseModel):
    """Структурированный результат парсинга ответа от Responses API"""

    output: dict[str, Any] | None = Field(None, description="Текст ответа модели в dict формате")
    raw_text: dict[str, Any] | str | None = Field(
        None, description="Сырой текстовый ответ модели, если JSON не ожидался"
    )
    tool_calls: list[ToolCallParsed] = Field(
        default_factory=list, description="Вызовы инструментов"
    )

    messages: list[dict[str, Any]] = Field(default_factory=list, description="Сообщения от модели")
    total_tokens: int = Field(description="Количество токенов")


class LLMImageResponse(BaseModel):
    """Структурированный результат парсинга ответа от Responses API"""

    size: str
    image: str = Field(description="Изображение в формате base64")
    total_tokens: int = Field(description="Количество токенов")
    output_format: str = "png"


class Runtime[B: BaseModel, T](BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    context: B
    state: T | None = None
    messages: list[dict[str, Any]] | str = Field(default_factory=list)


RequestT = TypeVar("RequestT", bound=BaseModel)
ResponseT = TypeVar("ResponseT", bound=BaseModel)


class LLMServiceProtocol(Protocol[RequestT, ResponseT]):  # pyright: ignore[reportInvalidTypeVarUse]
    base_url: str
    response_model: type[ResponseT]
    _session: ClientSession
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
