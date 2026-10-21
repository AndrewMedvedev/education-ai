from typing import NotRequired, TypedDict

import logging
import time
from asyncio import Semaphore, TaskGroup
from collections.abc import Callable
from uuid import UUID

from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import session_factory
from src.courses.agents.course_generator.subagents.protocols import TheoryAgent
from src.courses.agents.schemas import Context
from src.courses.application.domain_dtos import (
    LessonDict,
    LessonStructureDict,
)
from src.courses.application.mappers import dict_to_lesson, lesson_to_dict, model_to_typed_dict
from src.courses.application.repos import LessonRepository, VectorRepository
from src.courses.domain.entities import Lesson
from src.courses.domain.vo import AnyContentBlock, ContentType
from src.courses.infra.services.client import SrvCourseClient
from src.courses.utils.formatting import get_lesson_context
from src.llm_service import LLMTextService

from ..few_shots import LESSON_STRUCTURE_FEW_SHOT
from .prompts import LESSON_STRUCTURE_PROMPT, ContentSpecification, LessonStructure
from .protocols import IndexLesson

logger = logging.getLogger(__name__)


class LessonAgentState(TypedDict):
    """Состояние агента для создания модулей"""

    generation_context: Context
    module_id: UUID
    audience_description: str  # Описание целевой аудитории курса
    learning_objectives: list[str]  # Цели обучения курса
    order: int  # Порядковый номер урока
    lesson_description: str  # Описание урока из структуры модуля
    lesson_structure: NotRequired[LessonStructureDict]  # Структура/сценарий урока
    lesson: NotRequired[LessonDict]  # Сгенерированный урок


class LessonAgent:
    def __init__(
        self,
        client: SrvCourseClient,
        lesson_repo: Callable[
            [AsyncSession],
            LessonRepository,
        ],
        vector_repo: VectorRepository,
        theory_agent: TheoryAgent,
        index_lesson: IndexLesson,
        max_parallel: int = 4,
    ) -> None:
        self._client = client
        self._lesson_repo = lesson_repo
        self._vector_repo = vector_repo
        self._theory_agent = theory_agent
        self._index_lesson = index_lesson
        self.semaphore = Semaphore(max_parallel)

    async def plan_lesson_structure(
        self,
        state: LessonAgentState,
    ) -> dict[str, LessonStructureDict | LessonDict]:
        """Планирование структуры урока"""
        lesson_structure_planner = LLMTextService(
            client=self._client,
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
            "Module structure is done, start filling `title`, `description`, `learning_objectives`"
        )
        lesson = Lesson(
            module_id=state["module_id"],
            title=lesson_structure.title,
            description=lesson_structure.description,
            learning_objectives=lesson_structure.learning_objectives,
            order=state["order"],
            estimated_time_minutes=lesson_structure.estimated_time_minutes,
        )
        return {
            "lesson_structure": model_to_typed_dict(lesson_structure),
            "lesson": lesson_to_dict(lesson),
        }

    async def build_content_block(
        self,
        order: int,
        generation_context: Context,
        content_type: ContentType,
        content_plan: list[ContentSpecification],
        prompt: str,
        client: SrvCourseClient,
        lesson: Lesson,
    ) -> tuple[int, AnyContentBlock]:
        """Собирает контент-блок из входных данных для следующего шага сценария."""
        async with self.semaphore:
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
            content_block = await self._theory_agent(
                context=generation_context,
                content_type=content_type,
                prompt=prompt_template,
                client=client,
            )
            elapsed_time = time.monotonic() - start_time
            logger.info(
                "Added `%s` content block in lesson, generation time - %s seconds",
                content_type.value,
                round(elapsed_time, 2),
            )
            return order, content_block

    async def generate_content_blocks(
        self,
        state: LessonAgentState,
    ) -> dict[str, LessonDict]:
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
                    self.build_content_block(
                        order=order,
                        generation_context=state["generation_context"],
                        content_type=content.content_type,
                        content_plan=lesson_structure.content_plan,
                        prompt=content.prompt,
                        lesson=lesson,
                        client=self._client,
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

    async def save_lesson(self, state: LessonAgentState) -> None:
        """Сохраняет урок, чтобы результат был доступен после завершения операции."""
        lesson = dict_to_lesson(state["lesson"])  # type: ignore
        async with session_factory() as session:
            try:
                repo = self._lesson_repo(session)
                await repo.create_at(lesson)
                await session.commit()
                logger.info("Saving lesson '%s' to database ...", lesson.title)
            except IntegrityError:
                await session.rollback()
                logger.info("Lesson %s alredy exsists", lesson.title)

        await self._index_lesson.kiq(  # pyright: ignore[reportCallIssue]
            course_id=state["generation_context"].course_id,
            lesson_id=lesson.id,
        )


def build_lesson_graph(
    agent: LessonAgent,
    checkpointer: AsyncRedisSaver,
) -> CompiledStateGraph[LessonAgentState]:

    graph = StateGraph(LessonAgentState)

    graph.add_node("plan_lesson_structure", agent.plan_lesson_structure)
    graph.add_node("generate_content_blocks", agent.generate_content_blocks)
    graph.add_node("save_lesson", agent.save_lesson)
    graph.add_edge(START, "plan_lesson_structure")
    graph.add_edge("plan_lesson_structure", "generate_content_blocks")
    graph.add_edge("generate_content_blocks", "save_lesson")
    graph.add_edge("save_lesson", END)

    return graph.compile(checkpointer=checkpointer)
