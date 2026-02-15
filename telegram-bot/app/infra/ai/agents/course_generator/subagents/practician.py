# Суб агент - практик

import logging
from uuid import uuid4

from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from app.core.entities.course import (
    AnyAssignment,
    AssignmentType,
    FileUploadAssignment,
    GitHubAssignment,
    TestAssignment,
)
from app.settings import settings

from ..schemas import TeacherContext
from ..tools import knowledge_search

logger = logging.getLogger(__name__)

# Системные промпты для генерации разных типов практических заданий
SYSTEM_PROMPTS = {
    AssignmentType.TEST: """\
    Ты ассистент для создания теста к модулю, 7-10 качественных заданий/вопросов.
    Создай качественный тест, избегая коротких ответов (предпочти открытые вопросы
    или с объяснениями).

    Сначала используй свои знания. Вызывай инструменты только если нужна актуальная информация
    (например, свежие примеры кода). Экономь: не более 1-2 вызовов.
    """,
    AssignmentType.FILE_UPLOAD: """\
    Ты ассистент для создания задания с загрузкой файла.
    Создай детальное задание по запросу, включая описание, требования и критерии оценки
    """,
    AssignmentType.GITHUB: """\
    Ты ассистент для создания GitHub-задания.
    Опиши регламент (шаги, правила коммитов) и ожидаемый проект детально.
    """,
}

model = ChatOpenAI(
    api_key=settings.yandexcloud.api_key,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.2,
)

config = {
    AssignmentType.TEST: {
        "tools": [knowledge_search],
        "system_prompt": SYSTEM_PROMPTS[AssignmentType.TEST],
        "response_format": ProviderStrategy(TestAssignment),
    },
    AssignmentType.FILE_UPLOAD: {
        "system_prompt": SYSTEM_PROMPTS[AssignmentType.FILE_UPLOAD],
        "response_format": ProviderStrategy(FileUploadAssignment),
    },
    AssignmentType.GITHUB: {
        "tools": [knowledge_search],
        "system_prompt": SYSTEM_PROMPTS[AssignmentType.GITHUB],
        "response_format": ProviderStrategy(GitHubAssignment),
    },
}


async def call_practice_agent(
        assignment_type: AssignmentType, prompt: str, context: TeacherContext
) -> AnyAssignment:
    """Вызывает агента - генератора практических заданий для модуля

    :param assignment_type: Тип практического задания.
    :param prompt: Детальный промпт для генерации задания.
    :param context: Контекстная информация преподавателя.
    """

    logger.info("Calling practice agent for assignment type `%s` ...", assignment_type.value)
    agent = create_agent(
        model=model,
        context_schema=TeacherContext,
        checkpointer=InMemorySaver(),
        **config.get(assignment_type, {})
    )
    result = await agent.ainvoke(
        {"messages": [("human", prompt)]},
        context=context,
        config={"configurable": {"thread_id": f"{uuid4()}"}}
    )
    return result["structured_response"]
