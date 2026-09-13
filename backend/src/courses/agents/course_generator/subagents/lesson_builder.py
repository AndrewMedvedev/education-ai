from typing import NotRequired, TypedDict

import logging
import time
from asyncio import TaskGroup
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from sqlalchemy.exc import IntegrityError

from src.core.qdrant import qdrant_client
from src.llm_service import LLMTextService

from ....application.domain_dtos import (
    LessonDict,
    LessonStructureDict,
)
from ....application.mappers import dict_to_lesson, lesson_to_dict, model_to_typed_dict
from ....domain.entities import AnyContentBlock, ContentType, Lesson
from ....infra.database.repos.lesson import SqlLessonRepository
from ....infra.services import course_client
from ....infra.vector_repo import VectorRepository
from ....utils.formatting import get_content_blocks_context, get_lesson_context
from ...schemas import Context, RuntimeContext
from ..few_shots import LESSON_STRUCTURE_FEW_SHOT
from ..serializer import checkpointer
from .prompts import LESSON_STRUCTURE_PROMPT, ContentSpecification, LessonStructure
from .theorist import call_theory_agent

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Состояние агента для создания модулей"""

    generation_context: Context
    module_id: UUID
    audience_description: str  # Описание целевой аудитории курса
    learning_objectives: list[str]  # Цели обучения курса
    order: int  # Порядковый номер урока
    lesson_description: str  # Описание урока из структуры модуля
    lesson_structure: NotRequired[LessonStructureDict]  # Структура/сценарий урока
    lesson: NotRequired[LessonDict]  # Сгенерированный урок


async def plan_lesson_structure(
    state: AgentState,
) -> dict[str, LessonStructureDict | LessonDict]:
    """Планирование структуры урока"""
    lesson_structure_planner = LLMTextService(
        client=course_client,
        system_prompt=LESSON_STRUCTURE_PROMPT,
    )

    prompt_template = f"""\
    Спроектируй подробную структуру текущего урока.

    ## Контекст курса

    Целевая аудитория:
    {state["audience_description"]}

    Конечные цели обучения курса:
    {", ".join(state["learning_objectives"])}

    ## Текущий урок

    Положение урока внутри модуля:
    {state["order"]}

    ВАЖНО:
    порядковый номер используется только для понимания места урока
    в образовательной последовательности.

    Не добавляй его в title.
    Не используй названия вида "Урок {state["order"]}. ...".

    Описание и требования к содержанию урока:
    {state["lesson_description"]}

    ## Задача

    Спроектируй урок так, чтобы студент последовательно освоил тему
    и достиг предусмотренных образовательных результатов.

    Требования:

    - сформируй конкретный title без нумерации;
    - дай содержательное описание образовательной роли урока;
    - сформулируй проверяемые learning_objectives;
    - создай строго 4–5 логически связанных контент-блоков;
    - для каждого блока выбери content_type по смыслу;
    - для каждого блока составь подробный самодостаточный prompt;
    - каждый prompt должен содержать минимум 4–6 содержательных предложений;
    - не используй больше одного quiz;
    - не используй material будущих уроков как уже известный;
    - оцени реалистичное время прохождения урока.

    Каждый prompt должен точно указывать:
    - тему;
    - образовательную цель;
    - обязательное содержание;
    - необходимую глубину;
    - способ объяснения;
    - подходящий пример;
    - типичные ошибки, если они важны;
    - ожидаемый результат для студента.

    Верни результат строго по переданной JSON Schema.
    """
    logger.info(
        "Planning %s - module structure by description: '%s ...'",
        state["order"],
        state["lesson_description"][:100],
    )
    result = await lesson_structure_planner.invoke(
        schema=LessonStructure,
        messages=[
            *LESSON_STRUCTURE_FEW_SHOT,
            {"role": "user", "content": prompt_template},
        ],
    )

    lesson_structure = LessonStructure.model_validate(result.output)
    logger.info(
        "Module structure is done, start filling `title`, `description`, `learning_objectives` ..."
    )
    lesson = Lesson(
        module_id=state["module_id"],
        title=lesson_structure.title,
        description=lesson_structure.description,
        learning_objectives=lesson_structure.learning_objectives,
        order=state["order"],
    )
    return {
        "lesson_structure": model_to_typed_dict(lesson_structure),
        "lesson": lesson_to_dict(lesson),
    }


async def build_content_block(
    order: int,
    content_type: ContentType,
    generation_context: Context,
    content_plan: list[ContentSpecification],
    prompt: str,
    lesson: Lesson,
) -> tuple[int, AnyContentBlock]:
    """Собирает контент-блок из входных данных для следующего шага сценария."""
    start_time = time.monotonic()
    progress_percent = round((order / len(content_plan)) * 100, 2)
    logger.info(
        "%s%% Generating `%s` content block for current plan: '%s'",
        progress_percent,
        content_type.value,
        prompt[:100],
    )

    prompt_template = (
        "# Контекст текущего урока:\n"
        f"{get_lesson_context(lesson, include_content_blocks=False)}\n\n"
        f"# Сгенерируй контент блок с заданным типом - '{content_type.value}':\n"
        f"**Промпт**: {prompt}"
    )
    content_block = await call_theory_agent(
        content_type=content_type,
        context=generation_context,
        prompt=prompt_template,
        client=course_client,
    )
    elapsed_time = time.monotonic() - start_time
    logger.info(
        "Added `%s` content block in lesson, generation time - %s seconds",
        content_type.value,
        round(elapsed_time, 2),
    )
    return order, content_block


async def generate_content_blocks(state: AgentState) -> dict[str, LessonDict]:
    """Генерация контент блоков с помощью субагента - теоретика,
    используя сгенерированный план
    """

    lesson_structure_data = state["lesson_structure"]  # pyright: ignore[reportTypedDictNotRequiredAccess]

    lesson = dict_to_lesson(state["lesson"])  # pyright: ignore[reportTypedDictNotRequiredAccess]

    lesson_structure = LessonStructure.model_validate(lesson_structure_data)
    logger.info("Starting generate %s content blocks ...", len(lesson_structure.content_plan))

    async with TaskGroup() as tg:
        tasks = [
            tg.create_task(
                build_content_block(
                    order=order,
                    generation_context=state["generation_context"],
                    content_type=content.content_type,
                    content_plan=lesson_structure.content_plan,
                    prompt=content.prompt,
                    lesson=lesson,
                )
            )
            for order, content in enumerate(lesson_structure.content_plan, start=1)
        ]
    content_by_order = sorted(task.result() for task in tasks)
    for _, content in content_by_order:
        lesson.append_content_block(content)
    logger.info(
        "Saving generated content blocks of `%s` module to knowledge base ...",
        lesson.title,
    )

    return {"lesson": lesson_to_dict(lesson)}


async def save_lesson(state: AgentState, runtime: Runtime[RuntimeContext]) -> None:
    """Сохраняет урок, чтобы результат был доступен после завершения операции."""
    lesson = dict_to_lesson(state["lesson"])  # type: ignore  # ruff:ignore[blanket-type-ignore]
    try:
        await SqlLessonRepository(runtime.context.db_session).create(lesson)  # pyright: ignore[reportArgumentType]
        await runtime.context.db_session.commit()  # pyright: ignore[reportOptionalMemberAccess]
    except IntegrityError:
        await runtime.context.db_session.rollback()  # pyright: ignore[reportOptionalMemberAccess]
        logger.info("Lesson %s alredy exsists", lesson.title)
    await VectorRepository(client=qdrant_client).index_document(
        text=get_content_blocks_context(lesson.content_blocks),
        metadata={
            "course_id": state["generation_context"].course_id,
            "lesson_id": f"{lesson.id}",
            "source": f"{lesson.title}",
            "category": "theory",
        },
    )

    logger.info("Saving lesson '%s' to database ...", lesson.title)


graph = StateGraph(AgentState, context_schema=RuntimeContext)

graph.add_node("plan_lesson_structure", plan_lesson_structure)
graph.add_node("generate_content_blocks", generate_content_blocks)
graph.add_node("save_lesson", save_lesson)
graph.add_edge(START, "plan_lesson_structure")
graph.add_edge("plan_lesson_structure", "generate_content_blocks")
graph.add_edge("generate_content_blocks", "save_lesson")
graph.add_edge("save_lesson", END)

lesson_builder_agent = graph.compile(checkpointer=checkpointer)
