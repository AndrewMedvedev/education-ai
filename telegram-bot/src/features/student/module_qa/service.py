from uuid import UUID

from src.core.database import session_factory
from src.features.course import repository

from .ai_agent import qa_agent


async def ask_edu_assistant(module_id: UUID, user_id: int, question: str) -> str:
    async with session_factory() as session:
        module = await repository.get_module(session, module_id)
    thread_id = f"module-{module.id}-student-{user_id}"
    result = await qa_agent.ainvoke(
        {"messages": [("human", question)]},
        config={"configurable": {"thread_id": thread_id}},
        context=module,
    )
    return result["messages"][-1].content
