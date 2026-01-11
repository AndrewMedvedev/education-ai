from typing import Annotated, TypedDict

import logging
import operator
from collections.abc import Callable

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelRequest,
    ModelResponse,
    dynamic_prompt,
    wrap_model_call,
)
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

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


class PlannerContext(BaseModel):
    module_title: str
    module_description: str
    learning_sequence: list[SequenceStep]
    content_block: ContentBlock


@dynamic_prompt
def context_aware_prompt_for_planner(request: ModelRequest) -> str:
    prompt = (PROMPTS_DIR / "content_block_planner.md").read_text(encoding="utf-8")
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


class PlanExecution(TypedDict):
    input: PlannerContext
    plan: list[str]
    past_steps: Annotated[list[tuple[str, str]], operator.add]
    response: str


class Plan(BaseModel):
    steps: list[str] = Field(
        ..., description="Шаги для достижения цели, должны быть отсортированы по порядку"
    )


planner = create_agent(
    model=ChatOpenAI(
        api_key=settings.yandexcloud.apikey,
        model=settings.yandexcloud.aliceai_llm,
        base_url=settings.yandexcloud.base_url,
        temperature=0.5,
        max_retries=3,
        max_tokens=3000,
    ),
    middleware=[context_aware_prompt_for_planner],
    context_schema=PlannerContext,
    response_format=ToolStrategy(Plan)
)


class TaskExecutorContext(BaseModel):
    past_steps: list[tuple[str, str]] = Field(default_factory=list)
    current_step: str


@dynamic_prompt
def context_aware_prompt_for_task_executor(request: ModelRequest) -> str:
    prompt = (PROMPTS_DIR / "task_executor.md").read_text(encoding="utf-8")
    past_steps: list[tuple[str, str]] = request.runtime.context.past_steps
    current_step: str = request.runtime.context.current_step
    return prompt.format(
        past_steps="\n".join([
            f"({i + 1}) Задача: {task}. Результат выполнения: {result}"
            for i, (task, result) in enumerate(past_steps)
        ]),
        current_step=current_step,
    )


task_executor = create_agent(
    model=ChatOpenAI(
        api_key=settings.yandexcloud.apikey,
        model=settings.yandexcloud.yandexgpt_rc,
        base_url=settings.yandexcloud.base_url,
        temperature=0.3,
        max_retries=3
    ),
    tools=content_block_generator_tools,
    middleware=[context_aware_prompt_for_task_executor],
    context_schema=TaskExecutorContext,
    checkpointer=InMemorySaver()
)


def plan_node(state: PlanExecution) -> dict[str, list[str]]:
    """Создаёт пошаговый план для генерации контента"""

    logger.info("Compiling plan for content block generation ...")
    result = planner.invoke({"messages": []}, context=state["input"])
    logger.info("Compiled plan: %s", result["structured_response"].steps)
    return {"plan": result["structured_response"].steps}


def execute_task_node(state: PlanExecution) -> dict[str, list[tuple[str, str]]]:
    """Выполняет шаг из плана"""

    past_steps = state["past_steps"]
    step_number = len(past_steps)
    task = state["plan"][step_number]
    logger.info("Start execute (%s) task: %s", step_number, task)
    result = task_executor.invoke({"messages": []}, context=TaskExecutorContext(
        past_steps=past_steps, current_step=task
    ))
    last_message = result["messages"][-1].content
    logger.info("(%s) task execution finished", step_number)
    return {"past_steps": [(task, last_message)]}


def should_end(state: PlanExecution) -> bool:
    return len(state["past_steps"]) == len(state["plan"])


workflow = StateGraph(PlanExecution)

workflow.add_node("planner", plan_node)
workflow.add_node("task_executor", execute_task_node)

workflow.add_edge(START, "planner")
workflow.add_edge("planner", "task_executor")
workflow.add_conditional_edges(
    "task_executor",
    should_end,
    {True: END, False: "task_executor"},
)

agent = workflow.compile()
