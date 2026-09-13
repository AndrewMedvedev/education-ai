# pyright: reportOptionalMemberAccess=false, reportArgumentType=false, reportReturnType=false
from typing import NotRequired, TypedDict

import logging
import time
from asyncio.taskgroups import TaskGroup

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime as GraphRuntime
from sqlalchemy.exc import IntegrityError

from src.core.database import session_factory
from src.llm_service import LLMTextService, Runtime

from ...application.domain_dtos import CourseDict, CourseStructureDict, ModuleDict
from ...application.mappers import course_to_dict, dict_to_course, model_to_typed_dict
from ...domain.entities import Course
from ...domain.vo import CourseStatus
from ...infra.database.repos.course import SqlCourseRepository
from ...infra.services import course_client
from ..schemas import Context, RuntimeContext
from .few_shots import COURSE_STRUCTURE_FEW_SHOT
from .helper import invoke_or_resume
from .serializer import checkpointer
from .subagents.module_builder import module_builder_agent
from .subagents.prompts import COURSE_STRUCTURE_PROMPT, CourseStructure
from .subagents.reasoner import reasoner_agent

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    generation_context: Context  # Контекстная информация курса
    thinks: NotRequired[str]  # Мысли - план reasoning агента
    course_structure: NotRequired[CourseStructureDict]  # Сгенерированная структура курса
    course: NotRequired[CourseDict]  # Готовый курс


async def reasoning(state: AgentState) -> dict[str, str]:
    """Размышление над запросом преподавателя"""
    if state.get("thinks") is not None:
        return {"thinks": state.get("thinks", "")}
    start_time = time.monotonic()
    logger.info("Course generator in reasoning state ...")

    agent = reasoner_agent(
        runtime=Runtime(
            context=state["generation_context"],
            state=course_client,
        )
    )
    result = await agent.invoke(
        messages=[{"role": "user", "content": state["generation_context"].prompt}]
    )
    elapsed_time = time.monotonic() - start_time
    logger.info("Reasoning finished, time spent %s seconds", round(elapsed_time, 2))
    return {"thinks": result.raw_text}


async def plan_course_structure(state: AgentState) -> dict:
    """Планирование структуры курса используя информацию, полученную в ходе размышлений"""

    logger.info("Planning course structure using thinks: '%s ...'", state.get("thinks", "")[:150])

    agent = LLMTextService(
        client=course_client,
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


async def save_course(state: AgentState, runtime: GraphRuntime[RuntimeContext]) -> None:
    """Сохраняет курс, чтобы результат был доступен после завершения операции."""
    course_repos = SqlCourseRepository(runtime.context.db_session)
    course = dict_to_course(state["course"])  # pyright: ignore[reportTypedDictNotRequiredAccess]
    try:
        await course_repos.create(course)
        logger.info("Saving course '%s' to database ...", course.title)

        await runtime.context.db_session.commit()
    except IntegrityError:
        await runtime.context.db_session.rollback()
        logger.info("Course %s alredy exsists", course.title)


async def build_module(
    generation_context: Context,
    order: int,
    module_description: str,
    audience_description: str,
    learning_objectives: list[str],
) -> tuple[int, ModuleDict]:
    """Собирает модуль из входных данных для следующего шага сценария."""
    module_thread_id = f"course:{generation_context.course_id}:module:{order}"
    logger.info(
        "Generating module - %s, by description: '%s ...'", order, module_description[:150]
    )
    async with session_factory() as session:
        result = await invoke_or_resume(
            module_builder_agent,
            input_data={
                "generation_context": generation_context,
                "audience_description": audience_description,
                "learning_objectives": learning_objectives,
                "order": order,
                "module_description": module_description,
            },
            config=RunnableConfig(configurable={"thread_id": module_thread_id}),
            context=RuntimeContext(db_session=session),
        )
        return order, result["module"]


async def generate_modules(state: AgentState) -> dict[str, CourseDict]:
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
                build_module(
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


async def update_course(state: AgentState, runtime: GraphRuntime[RuntimeContext]) -> None:
    """Обновляет курс, чтобы синхронизировать сохранённое состояние."""
    course_repos = SqlCourseRepository(runtime.context.db_session)
    course = state["course"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
    await course_repos.update(
        uid=course["id"],
        status=CourseStatus.DRAFT,
    )
    logger.info("Update course '%s' to database ...", course["title"])

    await runtime.context.db_session.commit()


graph = StateGraph(AgentState, context_schema=RuntimeContext)

graph.add_node("reasoning", reasoning)
graph.add_node("plan_course_structure", plan_course_structure)
graph.add_node("save_course", save_course)
graph.add_node("generate_modules", generate_modules)
graph.add_node("update_course", update_course)
graph.add_edge(START, "reasoning")
graph.add_edge("reasoning", "plan_course_structure")
graph.add_edge("plan_course_structure", "save_course")
graph.add_edge("save_course", "generate_modules")
graph.add_edge("generate_modules", "update_course")
graph.add_edge("update_course", END)

agent = graph.compile(checkpointer=checkpointer)
