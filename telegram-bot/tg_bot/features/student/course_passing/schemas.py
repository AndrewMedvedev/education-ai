from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, NonNegativeInt, PositiveInt

from tg_bot.features.course.schemas import AnyAssignment
from tg_bot.utils import current_datetime


class StudentPractice(BaseModel):
    """Индивидуальное практическое задание для студента"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=current_datetime)
    module_id: UUID
    user_id: PositiveInt
    assignment: AnyAssignment
    ai_generated: bool = True


class Feedback(BaseModel):
    """Обратная связь на выполненную практику"""

    model_config = ConfigDict(from_attributes=True)

    submission_id: UUID
    user_id: PositiveInt
    error_overview: str = Field(..., description="Разбор ошибок")
    recommendations: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Индивидуальные рекомендации по улучшению"
    )


class Submission(BaseModel):
    """Сданная работа"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=current_datetime)
    practice_id: UUID
    user_id: PositiveInt
    score: NonNegativeFloat
    is_passed: bool = False


class PracticeProgress(BaseModel):
    practice_id: UUID
    submission_id: UUID | None = None
    user_id: PositiveInt
    best_score: NonNegativeFloat
    attempts: NonNegativeInt
    is_passed: bool = False
