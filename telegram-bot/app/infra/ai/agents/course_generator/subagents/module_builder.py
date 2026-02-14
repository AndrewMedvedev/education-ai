# Суб агент - для создания образовательного модуля

from typing import NotRequired, TypedDict

import logging
import time

from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.core.entities.course import AssignmentType, ContentType, Module
from app.settings import settings
from app.utils.formatting import get_module_context

from .practician import call_practice_agent
from .theorist import call_theory_agent

logger = logging.getLogger(__name__)

model = ChatOpenAI(
    api_key=settings.yandexcloud.api_key,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.2,
    max_retries=3
)


class ModuleStructure(BaseModel):
    """Структура модуля"""

    title: str = Field(description="Название модуля для студента")
    description: str = Field(description="Описание модуля для студента")
    content_plan: list[tuple[ContentType, str]] = Field(
        description="""Детальные промпты для генерации контент блоков с образовательным материалом.
        (должны быть в том порядке, в котором блоки будут идти внутри модуля)
        Для каждого блока content_scenario создавай детальный промпт, который:
         1. Учитывает контекст курса и модуля
         2. Содержит конкретный указания по содержанию
         3. Указывает стиль изложения
         4. Задаёт структуру контента
         5. Включает примеры если необходимо

        Виды контент блоков:
         - text - теоретический материал/лекция
         - program_code - пример с кодом и объяснением
         - mermaid - mermaid диаграмма (напиши только промпт для её генерации)
         - video - подходящее видео, которое нужно найти в интернете
         - quiz - вопросы для самопроверки
        """,
        min_length=3,
        examples=[
            [
                (ContentType.VIDEO, "Твой детальный промпт для поиска подходящего видео"),
                (ContentType.TEXT, "Здесь должен быть промпт для написания теоретического блока"),
                (ContentType.PROGRAM_CODE, "Детальное описание блока с программным кодом"),
            ]
        ]
    )
    assignment_specification: tuple[AssignmentType, str] = Field(
        description="""
        Детальный промпт для составления практического задания по пройденному материалу
        """,
        examples=[(AssignmentType.TEST, "Здесь должен быть промпт для генерации задания")]
    )


class AgentState(TypedDict):
    """Состояние агента для создания модулей"""

    audience_description: str  # Описание целевой аудитории курса
    learning_objectives: list[str]  # Цели обучения курса
    order: int  # Порядковый номер модуля
    module_description: str  # Описание модуля из структуры курса
    module_structure: NotRequired[ModuleStructure]  # Структура/сценарий модуля
    module: NotRequired[Module]  # Сгенерированный модуль


async def plan_module_structure(state: AgentState) -> dict[str, ModuleStructure | Module]:
    """Планирование структуры модуля"""

    module_structure_planner = create_agent(
        model=model,
        system_prompt="""\
        Ты полезный ассистент для планирования структуры образовательного модуля
        по его описанию. Ты пишешь задание для агентов, которые будут наполнять модуль контентом
        и заданиями. Учти что у агентов будут инструменты для web поиска,
        рисования mermaid диаграмм, поиска видео, книг и.т.д
        """,
        response_format=ProviderStrategy(ModuleStructure),
    )
    prompt_template = f"""\
    Сгенерируй структуру модуля используя следующую информацию:
     - **Целевая аудитория курса:** {state['audience_description']}
     - **Цели обучения курса:** {state['learning_objectives']}
     - **Порядковый номер модуля:** {state['order']}
     - **Описание модуля:** {state['module_description']}
    """
    logger.info(
        "Planning %s - module structure by description: '%s ...'",
        state["order"], state["module_description"][:100]
    )
    result = await module_structure_planner.ainvoke({"messages": [("human", prompt_template)]})
    module_structure = result["structured_response"]
    logger.info(
        "Module structure is done, start filling `title`, `description`, `learning_objectives` ..."
    )
    module = Module(
        title=module_structure.title,
        description=module_structure.description,
        learning_objectives=module_structure.learning_objectives,
        order=state["order"]
    )
    return {"module_structure": module_structure, "module": module}


async def generate_content_blocks(state: AgentState) -> dict[str, Module]:
    """Генерация контент блоков с помощью субагента - теоретика,
    используя сгенерированный план
    """

    module_structure, module = state["module_structure"], state["module"]
    logger.info("Starting generate %s content blocks ...", len(module_structure.content_plan))
    for i, (content_type, prompt) in enumerate(module_structure.content_plan, 1):
        start_time = time.monotonic()
        progress_percent = round((i / len(module_structure.content_plan)) * 100, 2)
        logger.info(
            "%s%% Generating `%s` content block for current plan: '%s'",
            progress_percent, content_type.value, prompt[:100]
        )
        prompt_template = (
            "# Контекст текущего модуля:"
            f"{get_module_context(module)}\n\n"
            "## Промпт для создания материала:\n"
            f"{prompt}"
        )
        content_block = await call_theory_agent(content_type, prompt_template)
        module.append_content_block(content_block)
        elapsed_time = time.monotonic() - start_time
        logger.info(
            "Added `%s` content block in module, generation time - %s seconds",
            content_type.value, round(elapsed_time, 2)
        )
    return {"module": module}


async def generate_assignment(state: AgentState) -> dict[str, Module]:
    """Генерация практического задания с помощью суб-агента по сгенерированному ТЗ"""

    module_structure, module = state["module_structure"], state["module"]
    assignment_type, prompt = module_structure.assignment_specification
    prompt_template = (
        "# Контекст текущего модуля:"
        f"{get_module_context(module)}\n\n"
        "## Промпт для создания практического задания:\n"
        f"{prompt}"
    )
    logger.info(
        "Generating `%s` assignment for prompt: '%s ...'", assignment_type.value, prompt
    )
    assignment = await call_practice_agent(assignment_type, prompt_template)
    module.add_assignment(assignment)
    return {"module": module}


# Создание рабочего пространства для агента
graph = StateGraph(AgentState)

graph.add_node("plan_module_structure", plan_module_structure)
graph.add_node("generate_content_blocks", generate_content_blocks)
graph.add_node("generate_assignment", generate_assignment)

graph.add_edge(START, "plan_module_structure")
graph.add_edge("plan_module_structure", "generate_content_blocks")
graph.add_edge("generate_content_blocks", "generate_assignment")
graph.add_edge("generate_assignment", END)

module_builder_agent = graph.compile()
