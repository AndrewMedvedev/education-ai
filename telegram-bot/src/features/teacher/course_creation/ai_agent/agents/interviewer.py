from typing import Any, NotRequired

import logging

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain.tools import ToolRuntime, tool
from langchain_core.messages import ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END
from langgraph.runtime import Runtime
from langgraph.types import Command
from pydantic import BaseModel, Field, PositiveInt

from src.core.config import settings
from src.rag import get_rag_pipeline

from ..prompts import INTERVIEW_SUMMARY_PROMPT, INTERVIEWER_PROMPT

logger = logging.getLogger(__name__)

model = ChatOpenAI(
    api_key=settings.yandexcloud.api_key,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.3,
    max_retries=3
)


class UserContext(BaseModel):
    user_id: PositiveInt


class State(AgentState):
    """Состояние интервью"""

    questions_count: int  # Текущее количество заданных вопросов
    summary: NotRequired[str]  # Основные выводы и инсайты полученные из интервью


class RAGSearchInput(BaseModel):
    """Входные параметры для поиска по прикреплённым материалам"""

    search_query: str = Field(description="Запрос для поиска")


@tool(
    "search_in_materials",
    description="Выполняет поиск по материалам преподавателя",
    args_schema=RAGSearchInput,
)
def rag_search(runtime: ToolRuntime[UserContext, State], search_query: str) -> str:
    index_name = f"materials-{runtime.context.user_id}-index"
    rag_pipeline = get_rag_pipeline(index_name=index_name)
    documents = rag_pipeline.retrieve(search_query)
    return "\n\n".join(documents)


@tool(
    "complete_interview",
    description="Завершает интервью для передачи данных следующему агенту"
)
async def finalize(runtime: ToolRuntime[UserContext, State]) -> Command:
    logger.info("Finishing interview session for teacher `%s`", runtime.context.user_id)
    prompt = ChatPromptTemplate.from_messages([("system", INTERVIEW_SUMMARY_PROMPT)])
    chain = prompt | model | StrOutputParser()
    logger.info(
        "Starting to summarize interview dialog with teacher `%s`",
        runtime.context.user_id
    )
    summary = await chain.ainvoke({"messages": [*runtime.state["messages"]]})
    tool_message = ToolMessage(content=summary, tool_call_id=runtime.tool_call_id)
    logger.info(
        "Interview complete successfully for user `%s`, interview summary: '%s ...'",
        runtime.context.user_id, summary[:500]
    )
    return Command(update={"messages": [tool_message], "summary": summary}, goto=END)


class LogInterviewMiddleware(AgentMiddleware):
    state_schema = State

    def after_model(  # noqa: PLR6301
            self, state: State, runtime: Runtime[UserContext]
    ) -> dict[str, Any] | None:
        questions_count = state.get("questions_count", 0)
        questions_count += 1
        logger.info(
            "[%s] Asking question to teacher `%s`, question: '%s ...'",
            questions_count, runtime.context.user_id, state["messages"][1].content[:100]
        )
        return {"questions_count": questions_count}


interviewer_agent = create_agent(
    model=model,
    context_schema=UserContext,
    system_prompt=INTERVIEWER_PROMPT,
    middleware=[LogInterviewMiddleware()],
    checkpointer=InMemorySaver(),
)
