from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, PositiveInt

from src.features.course.schemas import Module
from src.utils import current_datetime


class Group(BaseModel):
    """Группа студентов"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=current_datetime)
    course_id: UUID
    teacher_id: PositiveInt
    title: str
    is_active: bool = True


class Student(BaseModel):
    """Студент - пользователь, который проходит курс"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=current_datetime)
    user_id: PositiveInt | None = None
    group_id: UUID
    full_name: str
    login: str
    password_hash: str
    is_active: bool = False


class StudentProgress(BaseModel):
    """Прогресс студента на курсе"""

    model_config = ConfigDict(from_attributes=True)

    student_id: UUID
    started_at: datetime
    completed_at: datetime | None = None
    current_score: NonNegativeFloat = Field(default=0.0)
    current_module_id: UUID
    overall_percentage: NonNegativeFloat = Field(default=0.0)


class CourseProgress(BaseModel):
    student_id: UUID
    current_module_id: UUID
    total_modules: PositiveInt
    accessible_modules: list[Module]
