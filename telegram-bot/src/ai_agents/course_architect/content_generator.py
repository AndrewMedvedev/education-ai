from typing import Any

import logging
from collections.abc import Awaitable, Callable
from uuid import uuid4

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.agents.structured_output import ToolStrategy
from langchain.tools import tool
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel, Field

from ...core.courses import (
    CodeBlock,
    ContentType,
    ExerciseType,
    QuizBlock,
    TestExercise,
    TextBlock,
    VideoBlock,
)
from ...settings import settings
from ..tools import browse_page, draw_mermaid, rutube_search, web_search, write_code

logger = logging.getLogger(__name__)

SYSTEM_PROMPTS = {
    "code": """
    Ты полезный ассистент для создания примеров с кодом для студентов образовательного курса.
    Твоя задача по запросу создать максимально качественный контент.

    Используй инструмент `write_code` для генерации качественного кода.
    """,
    "text": """
    Ты полезный ассистент для написания образовательного-теоретического материала.
    Твоя задача написать максимально информативный и понятный материал по детальному запросу.

    ### Доступные инструменты
     - `web_search` - используя для проверки фактов или поиска необходимого материала
     - `browse_page` - используя для получения контента со страницы по её URL
     - `draw_mermaid` - используй для визуализации сложных процессов (построение диаграммы)
    """,
    "video": """
    Ты полезный ассистент для поиска и подбора видео для образовательных курсов.
    Твоя задача найти наиболее полезное видео по запросу/заданию,
    которое наилучшим способом впишется в текущий образовательный модуль.

    Используй инструмент `rutube_search` для поиска видео на платформе RuTube.
    """,
    "quiz": """
    Ты полезный ассистент для создания вопросов/теста для самопроверки пройденных знаний.
    Твоя задача создать тест, который затронет все ключевые темы и знания.

    Используй инструмент `web_search` для поиска достоверной информации.
    """
}

model = ChatOpenAI(
    api_key=settings.yandexcloud.apikey,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.5,
)


class ContentContext(BaseModel):
    """Контекст работы агента для генерации контента"""

    content_type: ContentType


class ContentTypeMiddleware(AgentMiddleware):
    async def awrap_model_call(  # noqa: PLR6301
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Динамически определяет модель поведения агента в зависимости от типа контента"""

        content_type = request.runtime.context.content_type
        config = {
            "code": {
                "tools": [write_code],
                "system_message": SystemMessage(content=SYSTEM_PROMPTS["code"]),
                "response_format": ToolStrategy(CodeBlock)
            },
            "text": {
                "tools": [web_search, browse_page, draw_mermaid],
                "system_message": SystemMessage(content=SYSTEM_PROMPTS["text"]),
                "response_format": ToolStrategy(TextBlock)
            },
            "video": {
                "tools": [rutube_search],
                "system_message": SystemMessage(content=SYSTEM_PROMPTS["video"]),
                "response_format": ToolStrategy(VideoBlock)
            },
            "quiz": {
                "tools": [web_search],
                "system_message": SystemMessage(content=SYSTEM_PROMPTS["quiz"]),
                "response_format": ToolStrategy(QuizBlock)
            }
        }
        return await handler(request.override(**config.get(content_type.value, {})))


def create_content_generator(content_type: ContentType):
    config = {
        "code": {
            "tools": [write_code],
            "system_prompt": SYSTEM_PROMPTS["code"],
            "response_format": ToolStrategy(CodeBlock),
        },
        "text": {
            "tools": [web_search, browse_page, draw_mermaid],
            "system_prompt": SYSTEM_PROMPTS["text"],
            "response_format": ToolStrategy(TextBlock),
        },
        "video": {
            "tools": [rutube_search],
            "system_prompt": SYSTEM_PROMPTS["video"],
            "response_format": ToolStrategy(VideoBlock),
        },
        "quiz": {
            "tools": [web_search],
            "system_prompt": SYSTEM_PROMPTS["quiz"],
            "response_format": ToolStrategy(QuizBlock),
        },
    }
    return create_agent(
        model=model,
        checkpointer=InMemorySaver(),
        **config.get(content_type.value, {})
    )


class ContentGeneratorInput(BaseModel):
    """Входные параметры для вызова агента - контент генератора"""

    content_type: ContentType = Field(
        description="Тип контент блока который нужно сгенерировать",
        examples=["text", "quiz", "code", "video"]
    )
    prompt: str = Field(description="Детальный промпт для генерации контента")


@tool(
    "generate_content",
    description="Вызывает агента для генерации образовательного контента",
    args_schema=ContentGeneratorInput,
)
async def call_content_generator(content_type: ContentType, prompt: str) -> dict[str, Any]:
    """Вызывает агента для генерации образовательного контента"""

    logger.info(
        "Call content generator agent with content type %s and prompt: '%s ...'",
        content_type.value, prompt[:500]
    )
    thread_id = f"{content_type}-{uuid4()}"
    content_generator = create_content_generator(content_type)
    result = await content_generator.ainvoke(
        {"messages": [{"role": "human", "content": prompt}]},
        config={"configurable": {"thread_id": thread_id}}
    )
    return result["structured_response"]


class ExerciseContext(BaseModel):
    """Контекст агента для генерации заданий"""

    exercise_type: ExerciseType


exercise_generator = create_agent(
    model=model,
    context_schema=ExerciseContext,
    response_format=ToolStrategy(TestExercise),
)


class ExerciseGeneratorInput(BaseModel):
    """Входные параметры агента для генерации практических заданий"""

    exercise_type: ExerciseType = Field(
        description="Тип задания по его виду выполнения",
        examples=["test", "file_upload", "github"]
    )
    prompt: str = Field(description="Детальный промпт для генерации задания")


@tool(
    "generate_exercise",
    description="Генерирует практическое задание для модуля образовательного курса",
    args_schema=ExerciseGeneratorInput,
)
async def call_exercise_generator(exercise_type: ExerciseType, prompt: str):
    thread_id = f"{exercise_type}-{uuid4()}"
    result = await exercise_generator.ainvoke(
        {"messages": [{"role": "human", "content": prompt}]},
        context=ExerciseContext(exercise_type=exercise_type),
        config={"configurable": {"thread_id": thread_id}}
    )
    return result["structured_response"]
