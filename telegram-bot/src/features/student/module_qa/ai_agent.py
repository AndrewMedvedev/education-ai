from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from src.core.config import settings
from src.features.course.schemas import Module
from src.features.course.utils import get_module_context

model = ChatOpenAI(
    api_key=settings.yandexcloud.api_key,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.2,
)

SYSTEM_PROMPT_TEMPLATE = (
    "Ты полезный ассистент внутри образовательной платформы."
    "Твоя быть максимально полезным для студента, отвечая на его вопросы."
    "Работай и отвечай только на вопросы касаемо контекста текущего модуля."
    "**Текущий модуль**: {module_context}"
)


@dynamic_prompt
def context_based_prompt(request: ModelRequest) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        module_context=get_module_context(request.runtime.context)
    )


qa_agent = create_agent(
    model=model,
    middleware=[context_based_prompt],
    context_schema=Module,
    checkpointer=InMemorySaver(),
)
