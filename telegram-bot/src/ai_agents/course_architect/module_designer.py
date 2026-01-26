import logging

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel, NonNegativeInt

from ...core.courses import Module
from ...settings import settings
from .content_generator import call_content_generator

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Ты профессиональный методист/разработчик модулей для образовательных курсов.
Твоя задача по создать полноценный модуль по сценарию курса.

**Целевая аудитория курса:** {audience_description}
**Цели обучения всего курса:** {learning_objectives}
**Сценарий для модуля с порядковым номером {order}:** {module_scenario}
"""


class ModuleContext(BaseModel):
    audience_description: str
    learning_objectives: list[str]
    order: NonNegativeInt
    module_scenario: str


@dynamic_prompt
def context_based_prompt(request: ModelRequest) -> str:
    context = request.runtime.context
    return SYSTEM_PROMPT.format(
        audience_description=context.audience_description,
        learning_objectives=", ".join(context.learning_objectives),
        order=context.order,
        module_scenario=context.module_scenario,
    )


model = ChatOpenAI(
    api_key=settings.yandexcloud.apikey,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.3,
    max_retries=3
)

module_designer = create_agent(
    model=model,
    tools=[call_content_generator],
    middleware=[context_based_prompt],
    response_format=ToolStrategy(Module),
    checkpointer=InMemorySaver(),
)
