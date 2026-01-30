from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel, NonNegativeInt

from src.core.config import settings
from src.features.course.schemas import Module

from .assignment_generator import call_assignment_generator
from .content_generator import call_content_generator

SYSTEM_PROMPT = """
Ты профессиональный методист/разработчик модулей для образовательных курсов.
Твоя задача по создать полноценный модуль по сценарию курса.

**Целевая аудитория курса:** {audience_description}
**Цели обучения всего курса:** {learning_objectives}
**Сценарий для модуля с порядковым номером {order}:** {module_description}
"""


class ModuleContext(BaseModel):
    """Контекст агента для создания модуля"""

    audience_description: str  # Описание целевой аудитории
    learning_objectives: list[str]  # Цели обучения
    order: NonNegativeInt  # Порядок модуля внутри курса
    module_description: str  # Описание модуля


@dynamic_prompt
def context_aware_prompt(request: ModelRequest) -> str:
    context = request.runtime.context
    return SYSTEM_PROMPT.format(
        audience_description=context.audience_description,
        learning_objectives=", ".join(context.learning_objectives),
        order=context.order,
        module_description=context.module_description,
    )


model = ChatOpenAI(
    api_key=settings.yandexcloud.api_key,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.3,
    max_retries=3
)

module_creator_agent = create_agent(
    model=model,
    tools=[call_content_generator, call_assignment_generator],
    middleware=[context_aware_prompt],
    response_format=ToolStrategy(Module),
    checkpointer=InMemorySaver(),
)
