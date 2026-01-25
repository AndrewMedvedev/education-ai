from typing import Literal

import logging

from langchain.agents import AgentState
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, PositiveInt

from ...settings import settings

logger = logging.getLogger(__name__)

model = ChatOpenAI(
    api_key=settings.yandexcloud.apikey,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.5,
    max_retries=3
)


class Context(BaseModel):
    user_id: PositiveInt
    interview_summary: str


class State(AgentState):
    active_agent: Literal[
        "scenario_writer",
        "modules_designer",
        "content_generator",
    ]
