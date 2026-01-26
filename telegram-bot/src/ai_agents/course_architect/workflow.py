from typing import NotRequired, TypedDict

import logging

from langgraph.graph import END, START, StateGraph

from ...core.courses import Course
from .module_designer import ModuleContext, module_designer
from .scenario_writer import CourseScenario, ScenarioContext, scenario_writer

logger = logging.getLogger(__name__)


class State(TypedDict):
    user_id: int  # Идентификатор пользователя в Telegram
    teacher_context: dict[str, str]
    scenario: NotRequired[CourseScenario]
    course: NotRequired[Course]


async def write_course_scenario(state: State) -> dict:
    """Написание сценария образовательного курса"""

    teacher_insights = state["teacher_context"].get("insights", "")
    result = await scenario_writer.ainvoke(
        {"messages": []}, context=ScenarioContext(
            teacher_insights=teacher_insights,
        )
    )
    scenario = result["structured_response"]
    course = Course(
        creator_id=state["user_id"],
        title=scenario.title,
        learning_objectives=scenario.learning_objectives,
    )
    return {"scenario": scenario, "course": course}


async def generate_modules(state: State) -> dict[str, Course]:
    scenario = state.get("scenario")
    if scenario is None:
        ...
    course = state.get("course")
    if course is None:
        ...
    modules = []
    for order, module_scenario in enumerate(scenario.modules):
        logger.info(
            "Start generate module %s/%s by scenario: '%s ...'",
            order, len(scenario.modules), module_scenario[:100]
        )
        result = await module_designer.ainvoke(
            {"messages": []},
            context=ModuleContext(
                audience_description=scenario.audience_description,
                learning_objectives=scenario.learning_objectives,
                order=order,
                module_scenario=module_scenario,
            ),
            config={"configurable": {"thread_id": f"{state['user_id']}"}}
        )
        print(result["structured_response"].model_dump())
        modules.append(result["structured_response"])
        print(modules)
    course.modules = modules
    return {"course": course}


workflow = StateGraph(State)

workflow.add_node("write_course_scenario", write_course_scenario)
workflow.add_node("generate_modules", generate_modules)

workflow.add_edge(START, "write_course_scenario")
workflow.add_edge("write_course_scenario", "generate_modules")
workflow.add_edge("generate_modules", END)

graph = workflow.compile()
