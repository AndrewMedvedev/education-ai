from uuid import UUID

from src.core.database import session_factory
from src.features.course import repository
from src.features.course.schemas import Assignment

from ..schemas import Feedback, StudentPractice
from .agents.qa import qa_agent


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


async def give_feedback_on_assignment() -> Feedback:
    """Получение обратной связи по выполненному заданию от AI"""


async def generate_student_practice(
        assignment_example: Assignment, user_id: int,
) -> StudentPractice:
    """Генерация индивидуального варианта практики для студента"""

    async with session_factory() as session:
        ...
