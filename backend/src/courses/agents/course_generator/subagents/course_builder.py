# pyright: reportReturnType=false
from typing import Any, NotRequired, TypedDict

import logging
import time
from asyncio import Semaphore
from asyncio.taskgroups import TaskGroup

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.courses.agents.course_generator.subagents.protocols import ReasonerAgent
from src.courses.application.domain_dtos import CourseDict, CourseStructureDict, ModuleDict
from src.courses.application.mappers import course_to_dict, dict_to_course, model_to_typed_dict
from src.courses.application.repos import CourseRepository
from src.courses.domain.entities import Course
from src.courses.domain.enums import CourseStatus
from src.courses.infra.services.client import SrvCourseClient
from src.llm_service import LLMTextService, Runtime

from ...schemas import Context
from ..few_shots import COURSE_STRUCTURE_FEW_SHOT
from ..helper import invoke_or_resume
from .module_builder import (
    ModuleAgentState,
)
from .prompts import COURSE_STRUCTURE_PROMPT, CourseStructure

logger = logging.getLogger(__name__)


class CourseAgentState(TypedDict):
    generation_context: Context  # Контекстная информация курса
    thinks: NotRequired[str]  # Мысли - план reasoning агента
    course_structure: NotRequired[CourseStructureDict]  # Сгенерированная структура курса
    course: NotRequired[CourseDict]  # Готовый курс


class CourseAgent:
    def __init__(
        self,
        session: AsyncSession,
        client: SrvCourseClient,
        repo: CourseRepository,
        module_agent: CompiledStateGraph[ModuleAgentState, Any],
        reasoner_agent: ReasonerAgent,
        max_parallel: int = 3,
    ):
        self._session = session
        self._client = client
        self._repo = repo
        self._module_agent = module_agent
        self._reasoner_agent = reasoner_agent
        self.semaphore = Semaphore(max_parallel)

    async def reasoning(
        self,
        state: CourseAgentState,
    ) -> dict[str, str]:
        """Размышление над запросом преподавателя"""
        if state.get("thinks") is not None:
            return {"thinks": state.get("thinks", "")}
        start_time = time.monotonic()
        logger.info("Course generator in reasoning state ...")

        agent = self._reasoner_agent(
            runtime=Runtime(
                context=state["generation_context"],
                state=self._client,
            )
        )
        result = await agent.invoke(
            messages=[{"role": "user", "content": state["generation_context"].prompt}]
        )
        elapsed_time = time.monotonic() - start_time
        logger.info("Reasoning finished, time spent %s seconds", round(elapsed_time, 2))
        return {"thinks": result.raw_text}

    async def plan_course_structure(
        self,
        state: CourseAgentState,
    ) -> dict[str, dict[str, Any]]:
        """Планирование структуры курса используя информацию, полученную в ходе размышлений"""

        logger.info(
            "Planning course structure using thinks: '%s ...'", state.get("thinks", "")[:150]
        )

        agent = LLMTextService(
            client=self._client,
            system_prompt=COURSE_STRUCTURE_PROMPT,
        )
        result = await agent.invoke(
            messages=[
                *COURSE_STRUCTURE_FEW_SHOT,
                {"role": "user", "content": state.get("thinks", "")},
            ],
            schema=CourseStructure,
        )
        course_structure = CourseStructure.model_validate(result.output)
        course = Course(
            id=state["generation_context"].course_id,
            creator_id=state["generation_context"].user_id,
            difficulty=course_structure.difficulty,
            status=CourseStatus.IN_GENERATION,
            title=course_structure.title,
            description=course_structure.description,
            learning_objectives=course_structure.learning_objectives,
            tags=course_structure.tags,
        )
        logger.info("Added `title`, `description` and `learning_objectives` in course")
        return {
            "course_structure": model_to_typed_dict(course_structure),
            "course": course_to_dict(course),
        }

    async def save_course(
        self,
        state: CourseAgentState,
    ) -> None:
        """Сохраняет курс, чтобы результат был доступен после завершения операции."""

        course = dict_to_course(state["course"])  # pyright: ignore[reportTypedDictNotRequiredAccess]
        try:
            await self._repo.create(course)
            logger.info("Saving course '%s' to database ...", course.title)
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            logger.info("Course %s alredy exsists", course.title)

    async def build_module(
        self,
        generation_context: Context,
        order: int,
        module_description: str,
        audience_description: str,
        learning_objectives: list[str],
    ) -> tuple[int, ModuleDict]:
        module_thread_id = f"course:{generation_context.course_id}:module:{order}"
        logger.info(
            "Generating module - %s, by description: '%s ...'", order, module_description[:150]
        )
        async with self.semaphore:
            result = await invoke_or_resume(
                self._module_agent,
                input_data={
                    "generation_context": generation_context,
                    "audience_description": audience_description,
                    "learning_objectives": learning_objectives,
                    "order": order,
                    "module_description": module_description,
                },
                config=RunnableConfig(configurable={"thread_id": module_thread_id}),
            )
            return order, result["module"]

    async def generate_modules(
        self,
        state: CourseAgentState,
    ) -> dict[str, CourseDict]:
        """Генерация модулей по структуре курса"""

        course_structure, course = state["course_structure"], state["course"]  # pyright: ignore[reportTypedDictNotRequiredAccess]

        start_time = time.monotonic()
        total_modules = len(course_structure["module_descriptions"])
        logger.info("Start generate %s modules ...", total_modules)

        # Создаём задачу для каждого модуля

        # Параллельный запуск
        async with TaskGroup() as tg:
            tasks = [
                tg.create_task(
                    self.build_module(
                        generation_context=state["generation_context"],
                        order=order,
                        module_description=desc,
                        audience_description=course_structure["audience_description"],
                        learning_objectives=course_structure["learning_objectives"],
                    )
                )
                for order, desc in enumerate(course_structure["module_descriptions"], start=1)
            ]

        # Собираем результаты в правильном порядке
        modules_by_order = sorted(task.result() for task in tasks)
        for _, module in modules_by_order:
            course["modules"].append(module)

        logger.info(
            "Successfully generated %s modules, spent time %s seconds",
            total_modules,
            round(time.monotonic() - start_time, 2),
        )
        return {"course": course}

    async def update_course(
        self,
        state: CourseAgentState,
    ) -> None:
        """Обновляет курс, чтобы синхронизировать сохранённое состояние."""
        course = state["course"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
        await self._repo.update(
            uid=course["id"],
            status=CourseStatus.DRAFT,
        )
        logger.info("Update course '%s' to database ...", course["title"])

        await self._session.commit()


def build_course_graph(
    agent: CourseAgent,
    checkpointer: AsyncRedisSaver,
) -> CompiledStateGraph[CourseAgentState]:

    graph = StateGraph(CourseAgentState)

    graph.add_node("reasoning", agent.reasoning)
    graph.add_node("plan_course_structure", agent.plan_course_structure)
    graph.add_node("save_course", agent.save_course)
    graph.add_node("generate_modules", agent.generate_modules)
    graph.add_node("update_course", agent.update_course)
    graph.add_edge(START, "reasoning")
    graph.add_edge("reasoning", "plan_course_structure")
    graph.add_edge("plan_course_structure", "save_course")
    graph.add_edge("save_course", "generate_modules")
    graph.add_edge("generate_modules", "update_course")
    graph.add_edge("update_course", END)

    return graph.compile(checkpointer=checkpointer)
