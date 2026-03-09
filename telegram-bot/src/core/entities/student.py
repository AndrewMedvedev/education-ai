from typing import Any, NotRequired, Self, TypedDict

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, NonNegativeInt, PositiveInt

from ..commons import current_datetime
from .course import AnyAssignment

PASSING_TEST_SCORE = 61


class Group(BaseModel):
    """Учебная группа курса"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    course_id: UUID
    title: str


class ModuleProgress(TypedDict):
    """Результаты студента внутри модуля"""

    test_score: float
    test_attempts: int
    is_test_passed: bool
    assignment_score: NotRequired[float]


class LearningProgress(BaseModel):
    """Прогресс в обучении"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    student_id: PositiveInt
    course_id: UUID
    started_at: datetime = Field(..., description="Дата начала прохождения курса")
    completed_at: datetime | None = Field(default=None, description="Дата завершения курса")
    total_score: NonNegativeFloat = Field(
        default=0.0, description="Общее количество баллов за практические задания"
    )
    current_module_id: UUID | None = Field(
        default=None, description="ID текущего модуля, который проходит студент"
    )
    score_per_module: dict[str, ModuleProgress] = Field(
        default_factory=dict,
        description="Баллы и результаты за каждый модуль",
        examples=[
            {
                "e11a0aaf-2bb4-4233-be14-9470d9637c86": {
                    "test_score": 61.3,
                    "test_attempts": 2,
                    "is_test_passed": True,
                    "assignment_score": 76.0,
                }
            }
        ]
    )

    @property
    def is_test_passed(self) -> bool:
        """Пройдено ли тестирование в текущем модуле"""

        return self.score_per_module[f"{self.current_module_id}"].get("is_test_passed", False)

    def check_is_test_passed(self, module_id: UUID) -> bool:
        """Проверка пройдено ли тестирование модуле"""

        return self.score_per_module.get(f"{module_id}", {}).get("is_test_passed", False)

    @classmethod
    def start(cls, student_id: int, course_id: UUID, first_module_id: UUID) -> Self:
        """Начало прохождения курса"""

        return cls(
            student_id=student_id,
            course_id=course_id,
            started_at=current_datetime(),
            current_module_id=first_module_id,
        )

    def increment_test_score(self, score: float) -> None:
        """Добавление баллов за тестирование к текущему модулю"""

        attempts = self.score_per_module.get(
            f"{self.current_module_id}", {}
        ).get("test_attempts", 0)
        attempts += 1
        self.score_per_module.update(
            {f"{self.current_module_id}": {
                "test_score": score,
                "test_attempts": attempts,
                "is_test_passed": score >= PASSING_TEST_SCORE,
            }}
        )

    def increment_assignment_score(self, score: float) -> None:
        """Добавление баллов за практическое задание"""

        self.score_per_module[f"{self.current_module_id}"].update({"assignment_score": score})
        self.total_score += score

    def switch_to_next_module(self, next_module_id: UUID) -> None:
        """Переход к следующему модулю"""

        self.current_module_id = next_module_id


class StudentTask(BaseModel):
    """Индивидуальное задание для студента"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    student_id: PositiveInt
    module_id: UUID
    assignment: AnyAssignment = Field(..., description="Сгенерированное задание")
    created_at: datetime = Field(default_factory=current_datetime)
    submission_data: dict[str, Any] | None = Field(
        default=None,
        description="Сдача практического задания",
        examples=[
            {"file_extension": ".pdf", "md_text": "Some Markdown text"},
            {"repo_url": "https://github.com/Andr171p/education-ai.git"}
        ]
    )
    completed_at: datetime | None = Field(default=None, description="Дата завершения задания")
    is_finished: bool = False

    def add_submission(self, submission_data: dict[str, Any]) -> None:
        """Сдать практическое задание"""

        self.submission_data = submission_data
        self.completed_at = current_datetime()
        self.is_finished = True


class DailyChatLimit(BaseModel):
    """Ежедневное лимитирование сообщений для чата с ИИ"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    user_id: PositiveInt = Field(..., description="ID пользователя")
    date: datetime = Field(default_factory=current_datetime, description="Текущая дата")
    max_count: PositiveInt = Field(
        default=10, description="Максимальное количество сообщений в день"
    )
    current_count: NonNegativeInt = Field(
        default=0, description="Текущее количество отправленных сообщений"
    )

    @property
    def is_reached(self) -> bool:
        """Достигнут ли максимальный лимит сообщений"""

        return self.current_count >= self.max_count

    def increment_count(self) -> None:
        """Увеличивает счётчик сообщений на 1"""

        self.current_count += 1
