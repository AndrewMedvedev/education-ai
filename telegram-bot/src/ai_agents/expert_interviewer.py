from typing import NotRequired

import logging
from pathlib import Path

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt
from langchain.tools import ToolRuntime, tool
from langchain_core.messages import ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END
from langgraph.types import Command
from pydantic import BaseModel, Field, PositiveInt

from src.rag import get_rag_pipeline
from src.settings import PROMPTS_DIR, settings

logger = logging.getLogger(__name__)

model = ChatOpenAI(
    api_key=settings.yandexcloud.apikey,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.3,
    max_retries=3
)

system_prompt = Path(PROMPTS_DIR / "expert_interviewer" / "system.md").read_text(encoding="utf-8")
summary_prompt = Path(
    PROMPTS_DIR / "expert_interviewer" / "summary.md"
).read_text(encoding="utf-8")


class Context(BaseModel):
    user_id: PositiveInt
    course_title: str


class State(AgentState):
    interview_summary: NotRequired[str]


class MaterialsSearchInput(BaseModel):
    """Входные параметры для поиска по прикреплённым материалам"""

    search_query: str = Field(description="Запрос для поиска")


@tool(
    "search_in_materials",
    description="Выполняет поиск по материалам эксперта",
    args_schema=MaterialsSearchInput,
)
def materials_search(runtime: ToolRuntime[Context, State], search_query: str) -> str:
    index_name = f"materials-{runtime.context.user_id}-index"
    rag_pipeline = get_rag_pipeline(index_name=index_name)
    documents = rag_pipeline.retrieve(search_query)
    return "\n\n".join(documents)


@tool(
    "complete_interview",
    description="Завершает интервью для передачи данных следующему агенту"
)
async def complete_interview(runtime: ToolRuntime[Context, State]) -> Command:
    from ..bot import bot, storage  # noqa: PLC0415

    logger.info("Starting completion of interview with expert `%s`", runtime.context.user_id)
    storage_key = StorageKey(
        bot_id=bot.id,
        user_id=runtime.context.user_id,
        chat_id=runtime.context.user_id,
    )
    context = FSMContext(storage=storage, key=storage_key)
    prompt = ChatPromptTemplate.from_messages([
        ("system", summary_prompt.format(course_title=runtime.context.course_title)),
    ])
    chain = prompt | model | StrOutputParser()
    summary = await chain.ainvoke({"messages": [*runtime.state["messages"]]})
    await bot.send_message(
        chat_id=runtime.context.user_id,
        text="🤖 Спасибо за уделённое время, передаю ответы AI методисту ..."
    )
    await context.clear()
    tool_message = ToolMessage(content=summary, tool_call_id=runtime.tool_call_id)
    logger.info("Interview complete successfully for expert `%s`", runtime.context.user_id)
    return Command(update={"messages": [tool_message], "interview_summary": summary}, goto=END)


@dynamic_prompt
def context_based_prompt(request: ModelRequest) -> str:
    return system_prompt.format(course_title=request.runtime.context.course_title)


interviewer_agent = create_agent(
    model=model,
    context_schema=Context,
    state_schema=State,
    tools=[materials_search, complete_interview],
    middleware=[context_based_prompt],
    checkpointer=InMemorySaver(),
)
