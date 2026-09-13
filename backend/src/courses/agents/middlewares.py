# pyright: reportOptionalMemberAccess=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportArgumentType=false
# ruff: file-ignore[unused-method-argument, magic-value-comparison]


from typing import Any

import asyncio
import base64
import json
import logging
import re
from collections.abc import Awaitable, Callable
from json import dumps
from uuid import uuid4

from pydantic import BaseModel
from pymorphy3 import MorphAnalyzer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.others import thread_executor, tokens_encoder
from src.llm_service import (
    BaseAgentMiddleware,
    LLMImageResponse,
    LLMImageServiceProtocol,
    LLMServiceProtocol,
    LLMTextResponse,
    LLMTextService,
    LLMTextServiceProtocol,
    Messages,
)
from src.llm_service.schemas import ToolCallParsed
from src.media.schemas import PresignedUploadRequest

from ..application.dtos import Chat as ChatSchema
from ..application.repos import (
    ChatRepository,
    Repository,
)
from ..domain.entities import Chat
from ..infra.media_client import MediaClient
from ..infra.services import course_client

logger = logging.getLogger(__name__)


morph = MorphAnalyzer()


class SummarizationMiddleware(BaseAgentMiddleware):
    def __init__(self, system_prompt: str, number_of_tokens: int) -> None:
        """Инициализирует объект и сохраняет зависимости, необходимые для дальнейшей работы."""
        self.number_of_tokens = number_of_tokens
        self.system_prompt = system_prompt
        self._router: LLMTextService = LLMTextService(
            client=course_client,
            system_prompt=self.system_prompt,
        )

    async def before_model(
        self,
        service: LLMServiceProtocol,
        messages: list[dict],
    ) -> list[dict]:
        """Выполняет шаг middleware `before_model`, чтобы расширить поведение агента без изменения сервиса."""
        str_messages = dumps(messages)
        count_tokens = len(tokens_encoder.encode(text=str_messages))
        if count_tokens >= self.number_of_tokens:
            result = await self._router.invoke(messages=messages)  # pyright: ignore[reportAttributeAccessIssue]
            return [{"role": "assistant", "content": result.raw_text}]
        return messages


class ToolCallLimitMiddleware(BaseAgentMiddleware):
    def __init__(self, tool_limits: dict[str, int]) -> None:
        """Инициализирует объект и сохраняет зависимости, необходимые для дальнейшей работы."""
        self.tool_limits = tool_limits

    @staticmethod
    def _is_tool_error(result: dict[str, Any]) -> bool:
        output = result.get("output")
        if not isinstance(output, str):
            return False
        try:
            parsed = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            return False
        return isinstance(parsed, dict) and "error" in parsed

    async def wrap_tool_call(
        self,
        service: LLMTextServiceProtocol,
        tool: ToolCallParsed,
        handler: Callable[[ToolCallParsed], Awaitable[dict]],
    ) -> dict:
        """Выполняет шаг middleware `wrap_tool_call`, чтобы расширить поведение агента без изменения сервиса."""
        if tool.name in self.tool_limits:
            if self.tool_limits[tool.name] > 0:
                result = await handler(tool)
                if not self._is_tool_error(result):
                    self.tool_limits[tool.name] -= 1
                return result
            callable_func = service.tools[tool.name]
            logger.info("The tool %s call has reached the limit", tool.name)
            return callable_func.to_tool_result(
                call_id=tool.call_id,
                result=f"The tool's call limit is exhausted, do not call again {tool.name}.",
            )
        return await super().wrap_tool_call(service, tool, handler)


class LemmatizationMiddleware(BaseAgentMiddleware):
    @staticmethod
    def normalize_text(text: str) -> str:
        """Нормализует text, чтобы сравнение и поиск работали стабильнее."""
        if not text or not isinstance(text, str):
            return text

        # Быстрое извлечение слов
        words = re.findall(r"\w+", text.lower())

        lemmas = []
        for word in words:
            if len(word) <= 2:
                lemmas.append(word)
                continue
            parsed = morph.parse(word)[0]
            lemmas.append(parsed.normal_form)

        return " ".join(lemmas)

    async def normalize_text_async(self, text: str) -> str:
        """Нормализует text async, чтобы сравнение и поиск работали стабильнее."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            thread_executor,
            self.normalize_text,
            text,
        )

    async def process_conversation(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Основная функция"""
        processed = []
        texts = []

        for msg in messages:
            new_msg = msg.copy()

            if msg.get("role") in {"user", "assistant"} and isinstance(msg.get("content"), str):
                task = await self.normalize_text_async(msg["content"])
                texts.append((task, new_msg))
            else:
                processed.append(new_msg)

        if texts:
            for (
                result,
                new_msg,
            ) in texts:  # порядок должен соответствовать texts.append((task, new_msg))
                new_msg["content"] = result
                processed.append(new_msg)

        return processed

    async def before_model(
        self,
        service: LLMTextServiceProtocol,
        messages: list[dict],
    ) -> list[dict]:
        """Выполняет шаг middleware `before_model`, чтобы расширить поведение агента без изменения сервиса."""
        return await self.process_conversation(messages)


class BaseSqlCheckpointer[EntityT, SchemaT: BaseModel | None = None](BaseAgentMiddleware):
    def __init__(
        self,
        repo: Repository,
        session: AsyncSession,
    ) -> None:
        """Инициализирует объект и сохраняет зависимости, необходимые для дальнейшей работы."""
        self.repo = repo
        self.session = session

    async def _create(self, entity: EntityT) -> None:
        """Выполняет внутренний шаг `_create`, чтобы скрыть детали реализации от публичного API."""
        await self.repo.create(entity)
        await self.session.commit()

    async def _read(self, *args, **kwargs) -> EntityT | None:
        """Выполняет внутренний шаг `_read`, чтобы скрыть детали реализации от публичного API."""
        return await self.repo.read(*args, **kwargs)

    async def _update(self, *args, **kwargs) -> None:
        """Выполняет внутренний шаг `_update`, чтобы скрыть детали реализации от публичного API."""
        await self.repo.update(*args, **kwargs)
        await self.session.commit()


class ChatCheckpointerMiddleware(BaseSqlCheckpointer[Chat, ChatSchema]):
    def __init__(
        self,
        repo: ChatRepository,
        session: AsyncSession,
    ) -> None:
        super().__init__(repo=repo, session=session)

    async def before_agent(
        self,
        service: LLMServiceProtocol,
        messages: Messages,
    ) -> list[dict[str, Any]]:
        """Достает историю чата перед циклом обработки запроса."""
        messages = (
            [{"role": "user", "content": messages}] if isinstance(messages, str) else messages
        )
        schema = Chat(
            id=service.runtime.state.chat_id,
            user_id=service.runtime.context.user_id,
            course_id=service.runtime.context.course_id,
            messages=messages,
        )
        data = await self._read(
            user_id=schema.user_id,
            course_id=schema.course_id,
            chat_id=service.runtime.state.chat_id,
        )
        if data is not None:
            return data.messages + messages
        await self._create(schema)
        return messages

    async def after_model(
        self,
        service: LLMServiceProtocol,
        response: LLMTextResponse,
    ) -> LLMTextResponse:
        """Обновляет сообщения после ответа модели."""
        messages = []

        for message in response.messages:
            role = message.get("role")
            if role in {"user", "assistant"}:
                messages.append(message)

        await self._update(
            chat_id=service.runtime.state.chat_id,
            user_id=service.runtime.context.user_id,
            course_id=service.runtime.context.course_id,
            messages=messages,
        )
        return response


class SaveImageMiddleware(BaseAgentMiddleware):
    async def after_model(  # ruff: ignore[no-self-use]
        self,
        service: LLMImageServiceProtocol,
        response: LLMImageResponse,
    ) -> LLMImageResponse:
        """Сохраняет изображение в s3 хранилище и обновляет ссылку в ответе."""
        file_bytes = base64.b64decode(response.image)
        filename = f"{uuid4()}.{response.output_format}"
        result = await MediaClient(client=course_client).save_image(
            request=PresignedUploadRequest(
                folder="course-images",
                filename=filename,
                owner_id=service.runtime.context.course_id,
                content_type=f"image/{response.output_format}",
            ),
            file=file_bytes,
        )
        response.image = result
        return response


class StopInterview(BaseAgentMiddleware):
    async def after_model(
        self,
        service: LLMServiceProtocol,
        response: LLMTextResponse,
    ) -> LLMTextResponse:
        task_id = self._get_task_id(service)
        if task_id:
            logger.info("Interview completed, task_id=%s", task_id)
            response.tool_calls = []  # останавливает рекурсию в _process_response
            response.raw_text = {"task_id": task_id}  # прячем payload в уже существующее поле
        return response

    @staticmethod
    def _get_task_id(service: LLMServiceProtocol) -> str | None:
        runtime = service.runtime
        if runtime is None or runtime.state is None:
            return None
        return getattr(runtime.state, "task_id", None)
