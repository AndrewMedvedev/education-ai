from typing import Annotated

import logging
import operator

from langchain.agents import AgentState, create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from pydantic import BaseModel, PositiveInt

from ...settings import PROMPTS_DIR, settings

logger = logging.getLogger(__name__)

model = ChatOpenAI(
    api_key=settings.yandexcloud.apikey,
    model=settings.yandexcloud.aliceai_llm,
    base_url=settings.yandexcloud.base_url,
    temperature=0.5,
    max_retries=3
)

system_prompt = (PROMPTS_DIR / "course_architect" / "interviewer.md").read_text(encoding="utf-8")


class Context(BaseModel):
    user_id: PositiveInt


class State(AgentState):
    interview: Annotated[list[tuple[str, str]], operator.add]
    tg_file_ids: Annotated[list[str], operator.add]
    is_finished: bool


@tool(
    "",
    description="",
    args_schema=...
)
def save_qa(question: str, answer: str) -> Command:
    logger.info("Saving QA, question: %s, answer: %s", question, answer)
    return Command(update={"interview": [(question, answer)]})


@tool(
    "",
    description="",
    args_schema=...
)
def finish_interview() -> Command:
    logger.info("Finishing interview")
    return Command(update={"is_finished": True})


agent = create_agent(
    model=model, tools=[save_qa, finish_interview], system_prompt=system_prompt,
)
