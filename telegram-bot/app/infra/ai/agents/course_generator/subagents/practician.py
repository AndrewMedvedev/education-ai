# Суб агент - практик

import logging
from uuid import uuid4

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain.agents.structured_output import ProviderStrategy
from langchain_openai import ChatOpenAI

from src.core.config import settings
from src.features.course.schemas import (
    AnyAssignment,
    AssignmentType,
    FileUploadAssignment,
    GitHubAssignment,
    TestAssignment,
)

from ...tools import browse_page, web_search

logger = logging.getLogger(__name__)

# Системные промпты для генерации разных типов практических заданий
SYSTEM_PROMPTS = {
    AssignmentType.TEST: """\
    Ты ассистент для создания теста к модулю. Создай качественный тест,
    избегай коротких ответов (предпочти открытые вопросы или с объяснениями).

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
        "tools": [web_search, browse_page],
        "middleware": [ToolCallLimitMiddleware(
            tool_name="web_search", run_limit=2, thread_limit=4
        )],
        "system_prompt": SYSTEM_PROMPTS[AssignmentType.TEST],
        "response_format": ProviderStrategy(TestAssignment),
    },
    AssignmentType.FILE_UPLOAD: {
        "system_prompt": SYSTEM_PROMPTS[AssignmentType.FILE_UPLOAD],
        "response_format": ProviderStrategy(FileUploadAssignment),
    },
    AssignmentType.GITHUB: {
        "system_prompt": SYSTEM_PROMPTS[AssignmentType.GITHUB],
        "response_format": ProviderStrategy(GitHubAssignment),
    },
}


async def call_practice_agent(assignment_type: AssignmentType, prompt: str) -> AnyAssignment:
    """Вызывает агента - генератора практических заданий для модуля

    :param assignment_type: Тип практического задания.
    :param prompt: Детальный промпт для генерации задания.
    """

    logger.info(
        "Calling practice agent for assignment type `%s` and prompt: '%s ...'",
        assignment_type.value, prompt[:500],
    )
    agent = create_agent(model=model, **config.get(assignment_type, {}))
    result = await agent.ainvoke(
        {"messages": [("human", prompt)]},
        config={"configurable": {"thread_id": f"{uuid4()}"}}
    )
    return result["structured_response"]
