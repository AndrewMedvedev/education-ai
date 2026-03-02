# Агент для проверки практических заданий студентов

from typing import Any

import logging

from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from langchain_openai import ChatOpenAI

from src.app.schemas import AssignmentResult
from src.core.entities.course import AnyAssignment
from src.settings import settings
from src.utils.formatting import get_assignment_context

logger = logging.getLogger(__name__)

model = ChatOpenAI(
    api_key=settings.yandexcloud.api_key,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.3,
)

SYSTEM_PROMPT = """\
Ты — AI-ассистент преподавателя, проверяющий практические задания студентов.
Тебе предоставляется:
 - **Контекст задания**: подробное описание задачи, требования, учебные цели и критерии оценивания.
 - **Работа студента**: расширение файла (например, .pdf, .py, .md)
   и извлечённое текстовое содержимое (`md_text`).

Твоя задача — оценить работу в соответствии с критериями задания
и выдать структурированный результат.

### Процесс оценивания:
1. **Пойми задание** – внимательно прочитайте контекст, чтобы уяснить ожидания,
   рубрику оценивания и особые указания.
2. **Изучи работу студента** – проанализируйте предоставленный текст.
   Для кода оцените корректность, эффективность, стиль и документирование.
   Для эссе — аргументацию, структуру, грамматику и соответствие теме.
   Используй расширение файла для определения типа работы.
3. **Выставление оценки** – руководствуйтесь критериями из контекста. Используй шкалу 0–100.
   Будь последовательным и объективным.
4. **Дай обратную связь** – напишите конструктивные комментарии, отмечая сильные стороны
   и области для улучшения. Будь конкретен, ссылайся на части работы или требования задания.
"""


async def call_assignment_checker(
        assignment: AnyAssignment, submission_data: dict[str, Any]
) -> AssignmentResult:
    """Вызвать агента для проверки практических заданий"""

    logger.info("Calling `%s` assignment checker agent ...", assignment.assignment_type)

    agent = create_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        response_format=ProviderStrategy(AssignmentResult),
    )
    prompt_template = (
        f"{get_assignment_context(assignment)}\n\n"
        "## Работа студента\n"
        f"**Расширение файла:** {submission_data.get('file_extension')}\n"
        "**Содержимое файла:**\n"
        f"{submission_data.get('md_text')}"
    )
    result = await agent.ainvoke({"messages": [("human", prompt_template)]})
    return result["structured_response"]
