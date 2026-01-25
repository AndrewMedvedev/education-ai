from typing import Any

import logging
from collections.abc import Awaitable, Callable

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.agents.structured_output import ToolStrategy
from langchain.tools import tool
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel, Field

from ...core.enums import ContentType
from ...core.schemas import CodeBlock, QuizBlock, TextBlock, VideoBlock
from ...settings import PROMPTS_DIR, settings
from ..tools import tools

logger = logging.getLogger(__name__)

SYSTEM_PROMPTS_DIR = PROMPTS_DIR / "course_architect" / "content_generator"

model = ChatOpenAI(
    api_key=settings.yandexcloud.apikey,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.5,
)


class ContentContext(BaseModel):
    """Контекст работы агента для генерации контента"""

    content_type: ContentType


class ContentTypeMiddleware(AgentMiddleware):
    async def awrap_model_call(  # noqa: PLR6301
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Динамически определяет модель поведения агента в зависимости от типа контента"""

        content_type = request.runtime.context.content_type
        match content_type:
            case ContentType.CODE:
                tools = [tool for tool in request.tools if tool.name == "write_code"]
                response_format = CodeBlock
                system_prompt_file = "code.md"
            case ContentType.TEXT:
                tools = [
                    tool for tool in request.tools
                    if tool.name in {"web_search", "browse_page", "draw_mermaid"}
                ]
                response_format = TextBlock
                system_prompt_file = "text.md"
            case ContentType.VIDEO:
                tools = [tool for tool in request.tools if tool.name == "rutube_search"]
                response_format = VideoBlock
                system_prompt_file = "video.md"
            case ContentType.QUIZ:
                tools = [
                    tool for tool in request.tools
                    if tool.name in {"web_search", "browse_page"}
                ]
                response_format = QuizBlock
                system_prompt_file = "quiz.md"
            case _:
                tools = request.tools
                response_format = TextBlock
                system_prompt_file = "text.md"
        system_prompt = (SYSTEM_PROMPTS_DIR / system_prompt_file).read_text(encoding="utf-8")
        return await handler(request.override(
            tools=tools,
            system_message=SystemMessage(content=system_prompt),
            response_format=ToolStrategy(response_format),
        ))


content_generator = create_agent(
    model=model,
    tools=tools,
    middleware=[ContentTypeMiddleware()],
    context_schema=ContentContext,
    response_format=ToolStrategy(TextBlock),
    checkpointer=InMemorySaver(),
)


class ContentGeneratorInput(BaseModel):
    """Входные параметры для вызова агента - контент генератора"""

    content_type: ContentType = Field(
        description="Тип контент блока который нужно сгенерировать",
        examples=["text", "quiz", "code", "video"]
    )
    prompt: str = Field(
        description="Детальный промпт для генерации контента"
    )


@tool(
    "generate_content",
    description="",
    args_schema=ContentGeneratorInput,
    response_format="content_and_artifact"
)
async def call_content_generator(content_type: ContentType, prompt: str) -> dict[str, Any]:
    """Вызывает агента для генерации образовательного контента"""

    result = await content_generator.ainvoke(
        {"messages": [("human", prompt)]},
        context=ContentContext(content_type=content_type)
    )
    return result["structured_response"]
