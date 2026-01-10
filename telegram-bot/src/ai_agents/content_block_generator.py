import logging
from collections.abc import Callable

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelRequest,
    ModelResponse,
    dynamic_prompt,
    wrap_model_call,
)
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from ..core import enums, schemas
from ..settings import PROMPTS_DIR, settings
from .module_designer import ContentBlock, SequenceStep
from .tools import content_block_generator_tools

logger = logging.getLogger(__name__)

model = ChatOpenAI(
    api_key=settings.yandexcloud.apikey,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.5,
    max_retries=3
)


class GeneratorContext(BaseModel):
    module_title: str
    module_description: str
    learning_sequence: list[SequenceStep]
    content_block: ContentBlock


@dynamic_prompt
def context_aware_prompt(request: ModelRequest) -> str:
    prompt = (PROMPTS_DIR / "content_block_generator.md").read_text(encoding="utf-8")
    learning_sequence: list[SequenceStep] = request.runtime.context.learning_sequence
    content_block: ContentBlock = request.runtime.context.content_block
    return prompt.format(
        module_title=request.runtime.context.module_title,
        module_description=request.runtime.context.module_description,
        learning_sequence="\n".join([
            f" - [{sequence_step.number}]: ({sequence_step.step_type}) "
            f"{sequence_step.purpose} "
            f"(примерное количество минут: {sequence_step.estimated_minutes})"
            for sequence_step in learning_sequence
        ]),
        **content_block.model_dump()
    )


@wrap_model_call
def context_based_output(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    block_type: enums.BlockType = request.runtime.context.content_block.block_type
    match block_type:
        case enums.BlockType.READING:
            request = request.override(response_format=schemas.ReadingBlock)
        case block_type.VIDEO:
            request = request.override(response_format=schemas.VideoBlock)
        case block_type.CODE_EXAMPLE:
            request = request.override(response_format=schemas.CodeExampleBlock)
        case _:
            request = request.override(response_format=schemas.TheoryBlock)
    return handler(request)


agent = create_agent(
    model=model,
    tools=content_block_generator_tools,
    middleware=[context_aware_prompt, context_based_output],
    context_schema=GeneratorContext,
)
