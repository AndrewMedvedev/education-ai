from typing import NotRequired, TypedDict

import logging
import time

from src.core.database import session_factory

from ....course import repository
from ....course.schemas import Course
from .agents.module_creator import module_creator_agent
from .agents.structure_planner import CourseStructure, structure_planner_agent

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    user_id: int  # Идентификатор пользователя
    interview_with_teacher: str  # Интервью с учителем (данные от агента интервьювера)
    course_structure: NotRequired[CourseStructure]  # Сгенерированная структура курса
    course: NotRequired[Course]  # Готовый курс


async def plan_course_structure(state: AgentState) -> dict:
    """Планирование структуры курса используя информацию полученную
    из интервью с преподавателем.
    """

    logger.info(
        "Planning course structure by interview: '%s ...'",
        state["interview_with_teacher"][:300]
    )
    result = await structure_planner_agent.ainvoke(
        {"messages": [("human", state["interview_with_teacher"])]},
    )
    course_structure = result["structured_response"]
    course = Course(
        creator_id=state["user_id"],
        title=course_structure.title,
        description=course_structure.description,
        learning_objectives=course_structure.learning_objectives,
    )
    return {"course_structure": course_structure, "course": course}


async def generate_modules(state: AgentState) -> dict[str, Course]:
    """Генерация модулей по плану курса"""

    course_structure, course = state["course_structure"], state["course"]
    start_time = time.time()
    total_modules = len(course_structure.module_descriptions)
    logger.info("Start generate %s modules ...", total_modules)
    for order, module_description in enumerate(course_structure.module_descriptions):
        logger.info(
            "Generating module - %s, by description: '%s ...'",
            order, module_description[:300]
        )
        result = await module_creator_agent.ainvoke({
            "audience_description": course_structure.audience_description,
            "learning_objectives": course_structure.learning_objectives,
            "order": order,
            "module_description": module_description,
        })
        course.modules.append(result["module"])
        progress_percent = order + 1 / total_modules * 100
        logger.info("Modules generation progress %.1f%%", progress_percent)
    logger.info(
        "Successfully generated %s modules, execution time %s seconds",
        total_modules, round(time.time() - start_time, 2)
    )
    return {"course": course}


async def generate_final_assessment(state: AgentState) -> dict[str, Course]:
    """Генерация финального ассессмента в образовательный курс"""


async def save_course(state: AgentState) -> dict[str, Course]:
    """Сохранение курса в базу данных"""

    course = state["course"]
    async with session_factory() as session:
        repository.save(session, course)
        await session.commit()
    logger.info("Course `%s` saves successfully", course.title)
    return {"course": course}
