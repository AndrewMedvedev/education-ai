from typing import Any

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
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


class LearningProgress(BaseModel):
    """Прогресс в обучении"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    student_id: PositiveInt
    course_id: UUID
    started_at: datetime
    completed_at: datetime | None = None
    total_score: NonNegativeFloat = Field(default=0.0)
    current_module_id: UUID | None = None
    score_per_module: dict[str, dict[str, int | float]] = Field(
        default_factory=dict,
        description="Баллы за каждый модуль",
        examples=[
            {"e11a0aaf-2bb4-4233-be14-9470d9637c86": {"score": 61.3, "attempts": 2}}
        ]
    )

    def increment_score(self, score: float) -> None:
        """Добавление баллов за тестирование к текущему модулю"""

        attempts = self.score_per_module.get(str(self.current_module_id), {}).get("attempts", 0)
        attempts += 1
        self.score_per_module.update(
            {str(self.current_module_id): {"score": score, "attempts": attempts}}
        )
        self.total_score = sum(module["score"] for module in self.score_per_module.values())

    def switch_to_next_module(self, next_module_id: UUID) -> None:
        """Переход к следующему модулю"""

        self.current_module_id = next_module_id
