from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, NonNegativeInt, PositiveInt

from ...utils import current_datetime
from .content_blocks import AnyContentBlock
from .exercises import AnyExercise


class Module(BaseModel):
    """Модуль - часть образовательного курса"""

    title: str = Field(..., description="Название модуля")
    description: str = Field(..., description="Описание модуля для студента")
    order: NonNegativeInt = Field(
        ..., description="Порядковый номер модуля внутри курса (начинается с 0)"
    )
    content_blocks: list[AnyContentBlock] = Field(
        default_factory=list,
        min_length=1,
        description="Контент блоки с материалом для изучения"
    )
    # exercise: AnyExercise = Field(..., description="Задание для закрепления материала")


class CourseStatus(StrEnum):
    GENERATING = "generating"  # Генерация курса
    IN_VALIDATION = "in_validation"  # На проверке преподавателя
    ACTIVE = "active"  # Курс открыт для изучения
    CLOSED = "closed"  # Курс закрыт


class FinalAssessment(BaseModel):
    """Финальный ассессмент в конце курса"""

    version: NonNegativeInt = Field(
        default=0,
        description="""
            Версия задания. 0 - оригинальная версия преподавателя.
            >0 - сгенерированные варианты для предотвращения списывания""",
    )
    task: str = Field(
        ...,
        description="""
        Текст задания, который увидит студент
        (может быть описание финального проекта, презентации, задачи для решения или иное)
        """
    )
    evaluation_criteria: list[str] = Field(..., description="Критерии для оценки")


class Course(BaseModel):
    """Модель образовательного курса"""

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=current_datetime)
    creator_id: PositiveInt
    status: CourseStatus = Field(default=CourseStatus.GENERATING)
    image_url: str | None = None
    title: str
    learning_objectives: list[str] = Field(default_factory=list, min_length=2)
    modules: list[Module] = Field(default_factory=list, min_length=1)
    final_assessment: FinalAssessment | None = None
