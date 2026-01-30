from typing import Any

import logging
from uuid import uuid4

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel, Field

from src.core.config import settings
from src.features.course.schemas import (
    CodeBlock,
    ContentType,
    QuizBlock,
    TextBlock,
    VideoBlock,
)

from ..tools import (
    browse_page,
    draw_mermaid,
    rutube_search,
    web_search,
    write_code,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPTS = {
    ContentType.CODE: """
    Ты полезный ассистент для создания примеров с кодом для студентов образовательного курса.
    Твоя задача по запросу создать максимально качественный контент.

    Используй инструмент `write_code` для генерации качественного кода.
    """,
    ContentType.TEXT: """
    Ты полезный ассистент для написания образовательного-теоретического материала.
    Твоя задача написать максимально информативный и понятный материал по детальному запросу.

    ### Доступные инструменты
     - `web_search` - используя для проверки фактов или поиска необходимого материала
     - `browse_page` - используя для получения контента со страницы по её URL
     - `draw_mermaid` - используй для визуализации сложных процессов (построение диаграммы)
    """,
    ContentType.VIDEO: """
    Ты полезный ассистент для поиска и подбора видео для образовательных курсов.
    Твоя задача найти наиболее полезное видео по запросу/заданию,
    которое наилучшим способом впишется в текущий образовательный модуль.

    Используй инструмент `rutube_search` для поиска видео на платформе RuTube.
    """,
    ContentType.QUIZ: """
    Ты полезный ассистент для создания вопросов/теста для самопроверки пройденных знаний.
    Твоя задача создать тест, который затронет все ключевые темы и знания.

    Используй инструмент `web_search` для поиска достоверной информации.
    """
}

model = ChatOpenAI(
    api_key=settings.yandexcloud.api_key,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.5,
)


def create_content_generator(content_type: ContentType):
    config = {
        ContentType.CODE: {
            "tools": [write_code],
            "system_prompt": SYSTEM_PROMPTS[ContentType.CODE],
            "response_format": ToolStrategy(CodeBlock),
        },
        ContentType.TEXT: {
            # "tools": [web_search, browse_page, draw_mermaid],
            "system_prompt": SYSTEM_PROMPTS[ContentType.TEXT],
            "response_format": ToolStrategy(TextBlock),
        },
        ContentType.VIDEO: {
            "tools": [rutube_search],
            "system_prompt": SYSTEM_PROMPTS[ContentType.VIDEO],
            "response_format": ToolStrategy(VideoBlock),
        },
        ContentType.QUIZ: {
            # "tools": [web_search],
            "system_prompt": SYSTEM_PROMPTS[ContentType.QUIZ],
            "response_format": ToolStrategy(QuizBlock),
        },
    }
    return create_agent(
        model=model,
        checkpointer=InMemorySaver(),
        **config.get(content_type, {})
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
    agent = create_content_generator(content_type)
    result = await agent.ainvoke(
        {"messages": [("human", prompt)]},
        config={"configurable": {"thread_id": thread_id}}
    )
    return result["structured_response"]
