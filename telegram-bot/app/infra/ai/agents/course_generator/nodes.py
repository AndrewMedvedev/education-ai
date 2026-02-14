from typing import NotRequired, TypedDict

import logging
import time
from uuid import uuid4

from app.core.entities.course import Course

from .schemas import TeacherContext
from .subagents.module_builder import module_builder_agent
from .subagents.reasoner import reasoner_agent
from .subagents.structure_planner import CourseStructure, structure_planner_agent

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    teacher_context: TeacherContext  # Контекстная информация преподавателя
    thinks: NotRequired[str]  # Мысли - план reasoning агента
    course_structure: NotRequired[CourseStructure]  # Сгенерированная структура курса
    course: NotRequired[Course]  # Готовый курс


async def reasoning(state: AgentState) -> dict[str, str]:
    """Размышление над запросом преподавателя"""

    if state.get("thinks") is not None:
        return {"thinks": state.get("thinks")}
    start_time = time.monotonic()
    logger.info("Course generator in reasoning state ...")
    result = await reasoner_agent.ainvoke(
        {"messages": []},
        context=state["teacher_context"],
        config={"configurable": {"thread_id": f"{uuid4()}"}}
    )
    elapsed_time = time.monotonic() - start_time
    logger.info("Reasoning finished, time spent %s seconds", round(elapsed_time, 2))
    return {"thinks": result["messages"][-1].content}


async def plan_course_structure(state: AgentState) -> dict:
    """Планирование структуры курса используя информацию, полученную в ходе размышлений"""

    logger.info(
        "Planning course structure using thinks: '%s ...'", state["thinks"][:150]
    )
    result = await structure_planner_agent.ainvoke({"messages": [("human", state["thinks"])]})
    course_structure = result["structured_response"]
    course = Course(
        creator_id=state["teacher_context"].user_id,
        title=course_structure.title,
        description=course_structure.description,
        learning_objectives=course_structure.learning_objectives,
    )
    logger.info("Added `title`, `description` and `learning_objectives` in course")
    return {"course_structure": course_structure, "course": course}


async def generate_modules(state: AgentState) -> dict[str, Course]:
    """Генерация модулей по структуре курса"""

    course_structure, course = state["course_structure"], state["course"]
    start_time = time.monotonic()
    total_modules = len(course_structure.module_descriptions)
    logger.info("Start generate %s modules ...", total_modules)
    for order, module_description in enumerate(course_structure.module_descriptions):
        logger.info(
            "Generating module - %s, by description: '%s ...'",
            order, module_description[:150]
        )
        result = await module_builder_agent.ainvoke({
            "teacher_context": state["teacher_context"],
            "audience_description": course_structure.audience_description,
            "learning_objectives": course_structure.learning_objectives,
            "order": order,
            "module_description": module_description,
        })
        course.append_module(result["module"])
        progress_percent = round((order + 1 / total_modules) * 100, 2)
        logger.info("Modules generation progress %s%%", progress_percent)
    logger.info(
        "Successfully generated %s modules, spent time %s seconds",
        total_modules, round(time.monotonic() - start_time, 2)
    )
    return {"course": course}


async def generate_final_assessment(state: AgentState) -> dict[str, Course]:
    """Генерация финального ассессмента в образовательный курс"""
