from uuid import UUID

from src.core.database import session_factory
from src.features.course import repository
from src.features.course.schemas import Assignment
from src.features.course.utils import get_assignment_context
from src.features.teacher.course_creation.ai_agent.agents.assignment_generator import (
    call_assignment_generator,
)

from .ai_agent import qa_agent


async def ask_edu_assistant(module_id: UUID, user_id: int, question: str) -> str:
    """Задать вопрос образовательному AI ассистенту в контексте текущего модуля.

    :param module_id: ID текущего модуля.
    :param user_id: ID пользователя.
    :param question: Вопрос пользователя.
    :returns: Сгенерированный ответ.
    """

    async with session_factory() as session:
        module = await repository.get_module(session, module_id)
    thread_id = f"module-{module.id}-student-{user_id}"
    result = await qa_agent.ainvoke(
        {"messages": [("human", question)]},
        config={"configurable": {"thread_id": thread_id}},
        context=module,
    )
    return result["messages"][-1].content


async def generate_individual_assignment(assignment_example: Assignment) -> ...:
    individual_assignment = await call_assignment_generator(
        assignment_type=assignment_example.assignment_type,
        prompt=""""""
    )
