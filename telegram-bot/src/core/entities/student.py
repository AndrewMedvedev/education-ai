from typing import Any

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveInt,
)

from ..commons import current_datetime
from .course import AnyAssignment


class Group(BaseModel):
    """Учебная группа курса"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    course_id: UUID
    title: str


class Student(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=current_datetime)
    user_id: PositiveInt
    username: str | None = None
    group_id: UUID
    full_name: str
    is_active: bool = False


class IndividualAssignment(BaseModel):
    """Индивидуальное задание для студента"""

    id: UUID = Field(default_factory=uuid4)
    student_id: UUID
    module_id: UUID
    version: PositiveInt
    data: AnyAssignment
    generated_at: datetime = Field(default_factory=current_datetime)
    is_active: bool = True


class Submission(BaseModel):
    """Попытка выполнения индивидуального задания"""

    student_id: UUID
    individual_assignment_id: UUID
    data: dict[str, Any] = Field(
        default_factory=dict,
        examples=[
            {"given_answers": [[0, 2], [1], [3], [3, 4]]},  # Тест
            {"document": "Markdown текст загруженного документа"},  # Задание с загрузкой файла
            {"repo_url": "https://github.com/Andr171p/education-ai.git"}  # GitHub репозиторий
        ]
    )
    score: float = Field(..., ge=0.0, le=100.0)
    ai_feedback: str | None = None
    checked_at: datetime = Field(default_factory=current_datetime)


class StudentProgress(BaseModel):
    """Прогресс студента на курсе"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    student_id: UUID
    course_id: UUID
    started_at: datetime
    completed_at: datetime | None = None
    completed_modules_count: NonNegativeInt = Field(default=0)
    total_modules_count: NonNegativeInt
    total_score: NonNegativeFloat = Field(default=0.0)
    overall_percentage: NonNegativeFloat = Field(default=0.0)
    current_module_id: UUID | None = None
