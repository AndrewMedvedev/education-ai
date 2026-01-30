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
    AssignmentType,
    FileUploadAssignment,
    GitHubAssignment,
    TestAssignment,
)

from ..tools import browse_page, web_search

logger = logging.getLogger(__name__)

# Системные промпты для генерации разных типов практических заданий
SYSTEM_PROMPTS = {
    AssignmentType.TEST: """
    Ты полезный ассистент для создания практического задания к модулю в виде теста.
    Твоя задача создать максимально качественное тестирование используя свои инструменты
    для адаптации заданий
    (старайся избегать односложных вариантов ответа)
    """,
    AssignmentType.FILE_UPLOAD: """
    Ты полезный ассистент для создания задания с загрузкой файла.
    Твоя задача создать максимально качественное задание по детальному запросу.
    """,
    AssignmentType.GITHUB: """
    Ты полезный ассистент для создания практического задания на платформе GitHub.
    Твоя задача подробно описать регламент выполнения задания и описать ожидаемый проект.
    """,
}

model = ChatOpenAI(
    api_key=settings.yandexcloud.api_key,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.5,
)


def create_assignment_generator(assignment_type: AssignmentType):
    """Создаёт агента для генерации практических заданий

    :param assignment_type: Тип практического задания, которое нужно сгенерировать
    """

    config = {
        AssignmentType.TEST: {
            # "tools": [web_search, browse_page],
            "system_prompt": SYSTEM_PROMPTS[AssignmentType.TEST],
            "response_format": ToolStrategy(TestAssignment),
        },
        AssignmentType.FILE_UPLOAD: {
            "system_prompt": SYSTEM_PROMPTS[AssignmentType.FILE_UPLOAD],
            "response_format": ToolStrategy(FileUploadAssignment),
        },
        AssignmentType.GITHUB: {
            "system_prompt": SYSTEM_PROMPTS[AssignmentType.GITHUB],
            "response_format": ToolStrategy(GitHubAssignment),
        },
    }
    return create_agent(
        model=model,
        checkpointer=InMemorySaver(),
        **config.get(assignment_type, {})
    )


class AssignmentGenerationInput(BaseModel):
    """Входные параметры для вызова агента - генератора практических заданий"""

    assignment_type: AssignmentType = Field(
        description="Тип задания, которое нужно сгенерировать",
        examples=["test", "file_upload", "github"],
    )
    prompt: str = Field(description="Детальный промпт для генерации задания")


@tool(
    "generate_assignment",
    description="Вызывает агента для генерации практических заданий",
    args_schema=AssignmentGenerationInput
)
async def call_assignment_generator(
        assignment_type: AssignmentType, prompt: str
) -> dict[str, Any]:
    logger.info(
        "Call assignment generator agent with content type %s and prompt: '%s ...'",
        assignment_type.value,
        prompt[:500],
    )
    thread_id = f"{assignment_type}-{uuid4()}"
    agent = create_assignment_generator(assignment_type)
    result = await agent.ainvoke(
        {"messages": [("human", prompt)]},
        config={"configurable": {"thread_id": thread_id}}
    )
    return result["structured_response"]
