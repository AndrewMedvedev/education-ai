import os
from uuid import UUID

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain.tools import ToolRuntime, tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from src.core.commons import current_datetime
from src.infra.db.conn import session_factory
from src.infra.db.repos import CourseRepository, StudentRepository
from src.settings import BASE_DIR, settings
from src.utils.formatting import get_module_context

from ..course_generator.tools import knowledge_search
from .memory import remember, search_memory
from .prompts import SUMMARY_PROMPT, SYSTEM_PROMPT
from .schemas import StudentContext

SQLITE_PATH = BASE_DIR / "checkpoint.sqlite"

model = ChatOpenAI(
    api_key=settings.yandexcloud.api_key,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.3,
)

summarization_middleware = SummarizationMiddleware(
    model=model,
    trigger=("tokens", 9000),
    keep=("messages", 30),
    summary_prompt=SUMMARY_PROMPT,
)


@tool(
    "get_current_module_context",
    description="Получение материала модуля, который студент проходит прямо сейчас",
)
async def get_current_module_context(runtime: ToolRuntime[StudentContext]) -> str:
    async with session_factory() as session:
        student_repo = StudentRepository(session)
        course_repo = CourseRepository(session)
        progress = await student_repo.get_learning_progress(runtime.context.user_id)
        module = await course_repo.get_module(progress.current_module_id)
    return get_module_context(module)


async def call_chatbot(course_id: UUID, user_id: int, user_prompt: str) -> str:
    """Вызов чат-бот агента для диалога со студентом в рамках его учебного прогресса"""

    async with AsyncSqliteSaver.from_conn_string(os.fspath(SQLITE_PATH)) as checkpointer:
        await checkpointer.setup()
        agent = create_agent(
            model=model,
            system_prompt=SYSTEM_PROMPT.format(current_datetime()),
            context_schema=StudentContext,
            middleware=[summarization_middleware],
            tools=[knowledge_search, get_current_module_context, remember, search_memory],
            checkpointer=checkpointer,
        )
        result = await agent.ainvoke(
            {"messages": [("human", user_prompt)]},
            context=StudentContext(course_id=course_id, user_id=user_id),
            config={"configurable": {"thread_id": f"{user_id}"}}
        )
    return result["messages"][-1].content
