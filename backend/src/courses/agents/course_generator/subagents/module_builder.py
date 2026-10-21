from typing import Any, NotRequired, TypedDict

import logging
import time
from asyncio import Semaphore, TaskGroup
from collections.abc import Callable
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import session_factory
from src.courses.agents.schemas import Context
from src.courses.application.domain_dtos import LessonDict, ModuleDict, ModuleStructureDict
from src.courses.application.mappers import dict_to_module, model_to_typed_dict, module_to_dict
from src.courses.application.repos import ModuleRepository
from src.courses.domain.entities import Module
from src.courses.infra.services.client import SrvCourseClient
from src.llm_service import LLMTextService

from ..few_shots import MODULE_STRUCTURE_FEW_SHOT
from ..helper import invoke_or_resume
from .lesson_builder import LessonAgentState
from .prompts import MODULE_STRUCTURE_PROMPT, ModuleStructure

logger = logging.getLogger(__name__)


class ModuleAgentState(TypedDict):
    """Состояние агента для создания модулей"""

    generation_context: Context
    audience_description: str  # Описание целевой аудитории курса
    learning_objectives: list[str]  # Цели обучения курса
    order: int  # Порядковый номер модуля
    module_description: str  # Описание модуля из структуры курса
    module_structure: NotRequired[ModuleStructureDict]  # Структура/сценарий модуля
    module: NotRequired[ModuleDict]  # Сгенерированный модуль


class ModuleAgent:
    def __init__(
        self,
        client: SrvCourseClient,
        module_repo: Callable[
            [AsyncSession],
            ModuleRepository,
        ],
        lesson_agent: CompiledStateGraph[LessonAgentState, Any],
        max_parallel: int = 4,
    ):
        self._client = client
        self._module_repo = module_repo
        self._lesson_agent = lesson_agent
        self.semaphore = Semaphore(max_parallel)

    async def plan_module_structure(
        self,
        state: ModuleAgentState,
    ) -> dict[str, ModuleStructureDict | ModuleDict]:
        """Планирование структуры модуля"""

        module_structure_planner = LLMTextService(
            client=self._client,
            system_prompt=MODULE_STRUCTURE_PROMPT,
        )
        prompt_template = f"""\
        Спроектируй структуру текущего учебного модуля.

        ## Контекст курса

        Целевая аудитория:
        {state["audience_description"]}

        Конечные цели обучения курса:
        {state["learning_objectives"]}

        ## Текущий модуль

        Положение модуля в последовательности курса:
        {state["order"]}

        ВАЖНО:
        порядковый номер используется только для понимания места модуля
        в образовательной траектории.

        Не добавляй этот номер в title.
        Не используй названия вида "Модуль {state["order"]}. ...".

        Описание и требования к содержанию модуля:
        {state["module_description"]}

        ## Задача

        Определи структуру модуля так, чтобы он:
        - соответствовал уровню целевой аудитории;
        - выполнял свою роль в общей программе;
        - достигал заявленных образовательных результатов;
        - состоял из последовательных уроков;
        - не требовал знаний, которые появятся только позже;
        - не дублировал материал соседних этапов;
        - содержал минимально достаточное количество уроков.

        Каждый урок должен представлять отдельный логический шаг
        в освоении материала.

        Верни результат строго по переданной JSON Schema.
        """
        logger.info(
            "Planning %s - module structure by description: '%s ...'",
            state["order"],
            state["module_description"][:100],
        )
        result = await module_structure_planner.invoke(
            messages=[
                *MODULE_STRUCTURE_FEW_SHOT,
                {"role": "user", "content": prompt_template},
            ],
            schema=ModuleStructure,
        )

        module_structure = ModuleStructure.model_validate(result.output)
        logger.info(
            "Module structure is done, start filling `title`, `description`, `learning_objectives`"
        )
        module = Module(
            course_id=state["generation_context"].course_id,
            title=module_structure.title,
            description=module_structure.description,
            learning_objectives=module_structure.learning_objectives,
            order=state["order"],
        )
        return {
            "module_structure": model_to_typed_dict(module_structure),
            "module": module_to_dict(module),
        }

    async def save_module(self, state: ModuleAgentState) -> None:
        """Сохраняет модуль, чтобы результат был доступен после завершения операции."""

        module = dict_to_module(state["module"])  # type: ignore
        async with session_factory() as session:
            try:
                repo = self._module_repo(session)
                await repo.create_at(module)
                logger.info("Saving module '%s' to database ...", module.title)

                await session.commit()
            except IntegrityError:
                await session.rollback()
                logger.info("Module %s alredy exsists", module.title)

    async def build_lesson(
        self,
        order: int,
        lesson_description: str,
        generation_context: Context,
        module_id: UUID,
        audience_description: str,
        learning_objectives: list[str],
    ) -> tuple[int, LessonDict]:
        async with self.semaphore:
            lesson_thread_id = (
                f"course:{generation_context.course_id}:module:{module_id}:lesson:{order}"
            )
            logger.info(
                "Generating lesson - %s, by description: '%s ...'", order, lesson_description[:150]
            )
            result = await invoke_or_resume(
                self._lesson_agent,
                input_data={
                    "generation_context": generation_context,
                    "module_id": module_id,
                    "audience_description": audience_description,
                    "learning_objectives": learning_objectives,
                    "order": order,
                    "lesson_description": lesson_description,
                },
                config=RunnableConfig(configurable={"thread_id": lesson_thread_id}),
            )
            return order, result["lesson"]

    async def generate_lessons(
        self,
        state: ModuleAgentState,
    ) -> dict[str, ModuleDict]:
        """Генерация уроков по структуре модуля"""

        module_structure, module = state["module_structure"], state["module"]  # type: ignore
        start_time = time.monotonic()
        total_lessons = len(module_structure["lessons_descriptions"])

        logger.info("Start generate %s lessons ...", total_lessons)
        async with TaskGroup() as tg:
            tasks = [
                tg.create_task(
                    self.build_lesson(
                        order=order,
                        lesson_description=desc,
                        generation_context=state["generation_context"],
                        module_id=module["id"],
                        audience_description=state["audience_description"],
                        learning_objectives=module_structure["learning_objectives"],
                    )
                )
                for order, desc in enumerate(module_structure["lessons_descriptions"], start=1)
            ]

        # Собираем результаты в правильном порядке
        lessons_by_order = sorted(task.result() for task in tasks)
        for _, lesson in lessons_by_order:
            module["lessons"].append(lesson)

        logger.info(
            "Successfully generated %s lessons, spent time %s seconds",
            total_lessons,
            round(time.monotonic() - start_time, 2),
        )
        return {"module": module}


def build_module_graph(
    agent: ModuleAgent,
    checkpointer: AsyncRedisSaver,
) -> CompiledStateGraph[ModuleAgentState]:
    graph = StateGraph(ModuleAgentState)

    graph.add_node("plan_module_structure", agent.plan_module_structure)
    graph.add_node("save_module", agent.save_module)
    graph.add_node("generate_lessons", agent.generate_lessons)

    graph.add_edge(START, "plan_module_structure")
    graph.add_edge("plan_module_structure", "save_module")
    graph.add_edge("save_module", "generate_lessons")
    graph.add_edge("generate_lessons", END)

    return graph.compile(checkpointer=checkpointer)
