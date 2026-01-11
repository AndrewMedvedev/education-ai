from typing import Annotated, TypedDict

import logging
import operator
import time
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
from .tools import response_compiler_tools, task_executor_tools

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
def context_aware_planner_prompt(request: ModelRequest) -> str:
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


class PlanExecution(TypedDict):
    input: PlannerContext
    plan: list[str]
    past_steps: Annotated[list[tuple[str, str]], operator.add]
    response: type[schemas.AnyBlockData]


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
    middleware=[context_aware_planner_prompt],
    context_schema=PlannerContext,
    response_format=ToolStrategy(Plan)
)


class TaskExecutorContext(BaseModel):
    past_steps: list[tuple[str, str]] = Field(default_factory=list)
    current_step: str


@dynamic_prompt
def context_aware_task_executor_prompt(request: ModelRequest) -> str:
    prompt = (PROMPTS_DIR / "task_executor.md").read_text(encoding="utf-8")
    past_steps: list[tuple[str, str]] = request.runtime.context.past_steps
    current_step: str = request.runtime.context.current_step
    return prompt.format(
        past_steps="\n".join([
            f"({i + 1}) **Задача:** {task}. **Результат выполнения:** {result}"
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
    tools=task_executor_tools,
    middleware=[context_aware_task_executor_prompt],
    context_schema=TaskExecutorContext,
    checkpointer=InMemorySaver()
)


class ResponseCompilerContext(BaseModel):
    """Контекст для агента составителя контента"""

    block_type: enums.BlockType
    past_steps: list[tuple[str, str]]


@dynamic_prompt
def context_aware_response_compiler_prompt(request: ModelRequest) -> str:
    system_prompt = (PROMPTS_DIR / "response_compiler.md").read_text(encoding="utf-8")
    block_type: enums.BlockType = request.runtime.context.block_type
    past_steps: list[tuple[str, str]] = request.runtime.context.past_steps
    return system_prompt.format(
        block_type=block_type.value,
        past_steps="\n".join([
            f"({i + 1}) **Задача:** {task}. **Результат выполнения:** {result}"
            for i, (task, result) in enumerate(past_steps)
        ]),
    )


@wrap_model_call
def context_based_response_compiler_output(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    block_type: enums.BlockType = request.runtime.context.block_type
    match block_type:
        case enums.BlockType.READING:
            request = request.override(response_format=schemas.ReadingBlock)
        case enums.BlockType.VIDEO:
            request = request.override(response_format=schemas.VideoBlock)
        case enums.BlockType.CODE_EXAMPLE:
            request = request.override(response_format=schemas.CodeExampleBlock)
        case _:
            request = request.override(response_format=schemas.TheoryBlock)
    return handler(request)


response_compiler = create_agent(
    model=ChatOpenAI(
        api_key=settings.yandexcloud.apikey,
        model=settings.yandexcloud.yandexgpt_rc,
        base_url=settings.yandexcloud.base_url,
        temperature=0.3,
        max_retries=3
    ),
    tools=response_compiler_tools,
    middleware=[context_based_response_compiler_output, context_aware_response_compiler_prompt],
    context_schema=ResponseCompilerContext,
    checkpointer=InMemorySaver()
)


def plan_node(state: PlanExecution) -> dict[str, list[str]]:
    """Создаёт пошаговый план для генерации контента"""

    logger.info("📝 Planing for content block generation ...")
    result = planner.invoke({"messages": []}, context=state["input"])
    logger.info("📌 Plan: %s", result["structured_response"].steps)
    return {"plan": result["structured_response"].steps}


def execute_task_node(state: PlanExecution) -> dict[str, list[tuple[str, str]]]:
    """Выполнение задачи из плана"""

    past_steps = state["past_steps"]
    step_number = len(past_steps)
    current_step = state["plan"][step_number]
    logger.info("[Start execute (%s) task]: `%s`", step_number + 1, current_step)
    start_time = time.time()
    result = task_executor.invoke({"messages": []}, context=TaskExecutorContext(
        past_steps=past_steps, current_step=current_step
    ))
    execution_time = round(time.time() - start_time, 2)
    last_message = result["messages"][-1].content
    logger.info("[(%s) task execution finished]: %s s", step_number + 1, execution_time)
    return {"past_steps": [(current_step, last_message)]}


def should_continue_execution(state: PlanExecution) -> bool:
    """Определяет нужно ли продолжать выполнение задач"""

    return len(state["past_steps"]) == len(state["plan"])


def compile_response_node(state: PlanExecution) -> dict[str, schemas.AnyBlockData]:
    """Составляет финальный ответ"""

    logger.info("💡 Compiling task results to final response...")
    result = response_compiler.invoke(context=ResponseCompilerContext(
            block_type=state["input"].content_block.block_type,
            past_steps=state["past_steps"],
        )
    )
    print(result)
    return {"response": result["structured_response"]}


workflow = StateGraph(PlanExecution)

workflow.add_node("planner", plan_node)
workflow.add_node("task_executor", execute_task_node)
workflow.add_node("response_compiler", compile_response_node)

workflow.add_edge(START, "planner")
workflow.add_edge("planner", "task_executor")
workflow.add_conditional_edges(
    "task_executor",
    should_continue_execution,
    {True: "response_compiler", False: "task_executor"},
)
workflow.add_edge("response_compiler", END)

agent = workflow.compile()
