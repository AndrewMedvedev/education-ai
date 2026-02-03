from typing import NotRequired, TypedDict

from langchain.agents import create_agent
from langchain.agents.structured_output import ProviderStrategy
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from src.core.config import settings
from src.features.course.schemas import AssignmentType, ContentType, Module

from .assignment_generator import call_assignment_generator
from .content_generator import ModuleContext, call_content_generator

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
    content_scenario: list[tuple[ContentType, str]] = Field(
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
        system_prompt="""Ты полезный ассистент для планирования структуры образовательного модуля
        по его описанию. Ты пишешь задание для агентов, которые будут наполнять модуль контентом
        и заданиями. Учти что у агентов будут инструменты для web поиска,
        рисования mermaid диаграмм, поиска видео, книг и.т.д
        """,
        response_format=ProviderStrategy(ModuleStructure),
    )
    prompt_template = f"""
    Сгенерируй структуру модуля используя следующую информацию:
     - **Целевая аудитория курса:** {state['audience_description']}
     - **Цели обучения курса:** {state['learning_objectives']}
     - **Порядковый номер модуля:** {state['order']}
     - **Описание модуля:** {state['module_description']}
    """
    result = await module_structure_planner.ainvoke({"messages": [("human", prompt_template)]})
    module_structure = result["structured_response"]
    module = Module(
        title=module_structure.title,
        description=module_structure.description,
        order=state["order"]
    )
    return {"module_structure": module_structure, "module": module}


async def generate_content_blocks(state: AgentState) -> dict[str, Module]:
    """Генерация контент блоков с помощью суб-агента по расписанному сценарию"""

    module_structure, module = state["module_structure"], state["module"]
    for content_type, prompt in module_structure.content_scenario:
        content_block = await call_content_generator(
            content_type, prompt, context=ModuleContext(
                title=module_structure.title, description=module_structure.description
            )
        )
        module.content_blocks.append(content_block)
    return {"module": module}


async def generate_assignment(state: AgentState) -> dict[str, Module]:
    """Генерация практического задания с помощью суб-агента по сгенерированному ТЗ"""

    module_structure, module = state["module_structure"], state["module"]
    assignment_type, prompt = module_structure.assignment_specification
    assignment = await call_assignment_generator(assignment_type, prompt)
    module.assignment = assignment
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

module_creator_agent = graph.compile()
