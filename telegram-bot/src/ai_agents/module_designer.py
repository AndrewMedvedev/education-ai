import logging
from uuid import UUID

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt
from langchain.agents.structured_output import ToolStrategy
from langchain.tools import ToolRuntime, tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, NonNegativeInt, PositiveInt

from ..core import enums, schemas
from ..rag.attached_materials import search_materials
from ..settings import PROMPTS_DIR, settings
from .course_structure_planner import ModuleNote

logger = logging.getLogger(__name__)

model = ChatOpenAI(
    api_key=settings.yandexcloud.apikey,
    model=settings.yandexcloud.aliceai_llm,
    base_url=settings.yandexcloud.base_url,
    temperature=0.5,
    max_retries=3
)


class DesignerContext(BaseModel):
    course_id: UUID
    teacher_inputs: schemas.TeacherInputs
    course_description: str
    module_note: ModuleNote


@tool(parse_docstring=True)
async def attached_materials_search(runtime: ToolRuntime, query: str) -> list[str]:
    """Выполняет поиск по прикреплённым материалам к курсу по запросу

    Args:
        query: Запрос для поиска.
    """

    logger.info("Calling `attached_materials_search` tool with query: `%s`", query)
    return await search_materials(course_id=runtime.context.course_id, query=query)


class SequenceStep(BaseModel):
    number: NonNegativeInt = Field(..., description="Порядковый номер шага (нумерация с 0)")
    step_type: str = Field(
        ...,
        description="Тип шага в последовательности обучения",
        examples=["Практика", "Введение", "захват внимания"]
    )
    purpose: str = Field(..., description="Цели которые нужно достичь")
    estimated_minutes: PositiveInt = Field(..., description="Примерное количество минут")


class ContentBlock(BaseModel):
    block_type: enums.BlockType = Field(
        ...,
        description=f"Тип контент блока, может быть: {', '.join(list(enums.BlockType))}"
    )
    main_concept: str = Field(..., description="Основная концепция")
    key_points: list[str] = Field(..., description="Ключевые моменты")
    specification: str = Field(..., description="Подробное ТЗ для создания контент блока")


class AssessmentFramework(BaseModel):
    assessment_type: enums.AssessmentType = Field(
        ...,
        description=f"Тип ассессмента, может быть: {', '.join(list(enums.AssessmentType))}"
    )
    purpose: str = Field(..., description="Основная цель ассессмента")
    difficulty: str = Field(
        ...,
        description="Уровень сложности",
        examples=["easy", "medium", "hard"]
    )
    specification: str = Field(..., description="Подробное ТЗ для создания ассессмента")


class ModuleDesign(BaseModel):
    """Дизайн модуля курса"""

    learning_sequence: list[SequenceStep] = Field(
        ..., description="Последовательность обучения"
    )
    content_blueprint: list[ContentBlock] = Field(
        ..., description="План содержания контент блоков"
    )
    assessment_frameworks: list[AssessmentFramework] = Field(
        ..., description="План для систем оценки"
    )


@dynamic_prompt
def inject_module_note_in_system_prompt(request: ModelRequest) -> str:
    prompt = (PROMPTS_DIR / "module_designer.md").read_text(encoding="utf-8")
    teacher_inputs: schemas.TeacherInputs = request.runtime.context.teacher_inputs
    course_description: str = request.runtime.context.course_description
    module_note: ModuleNote = request.runtime.context.module_note
    return prompt.format(
        teacher_prompt=teacher_inputs.to_prompt(),
        course_description=course_description,
        **module_note.model_dump()
    )


agent = create_agent(
    model=model,
    tools=[attached_materials_search],
    context_schema=DesignerContext,
    middleware=[inject_module_note_in_system_prompt],
    response_format=ToolStrategy(ModuleDesign)
)
