from __future__ import annotations

from typing import Any, Self, TypeVar

from abc import ABC
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveInt,
    ValidationError,
    model_validator,
)

from ..utils import current_datetime
from .enums import AssessmentType, ContentType, ExerciseType, UserRole


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PositiveInt
    username: str | None = None
    role: UserRole
    created_at: datetime = Field(default_factory=current_datetime)


class Student(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: PositiveInt | None = None
    course_id: UUID
    created_by: PositiveInt
    full_name: str
    login: str
    password_hash: str
    is_active: bool = False

    @model_validator(mode="after")
    def validate_student(self) -> Self:
        if (self.is_active and self.user_id is None) or \
                (not self.is_active and self.user_id is not None):
            raise ValidationError("Student can only be active after identification!")
        return self


class Course(BaseModel):
    """Модель образовательного курса"""

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=current_datetime)
    creator_id: PositiveInt
    image_url: str | None = None
    title: str
    learning_objectives: list[str] = Field(default_factory=list)
    modules: list[Module] = Field(default_factory=list)
    assessment: Assessment


class Module(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    order: NonNegativeInt
    content_blocks: list[AnyContentBlock] = Field(default_factory=list)
    exercise: Exercise


class Exercise(ABC, BaseModel):
    """Базовая модель для создания упражнений/заданий"""

    exercise_type: ExerciseType
    version: NonNegativeInt = Field(
        default=0,
        description="""
        Версия задания. 0 - оригинальная версия преподавателя.
        >0 - сгенерированные варианты для предотвращения списывания"""
    )
    title: str = Field(..., description="Название")
    max_score: PositiveInt = Field(
        ..., description="Максимальное количество баллов, которое можно получить за выполнение"
    )
    passing_score: PositiveInt = Field(
        ..., description="Минимальное количество баллов, которое нужно набрать чтобы сдать задание"
    )


class TestQuestion(BaseModel):
    """Вопрос внутри тестирования"""

    text: str = Field(..., description="Формулировка вопроса")
    options: list[str] = Field(
        default_factory=list, description="Варианты ответов (порядок имеет значение)"
    )
    correct_answers: list[int] = Field(
        default_factory=list,
        description="Индексы правильных ответов начиная с 0",
        examples=[{0, 3, 4}, {1}, {2, 5}]
    )
    points: PositiveInt = Field(..., description="Количество баллов за правильный ответ")


class TestExercise(Exercise):
    """Задание в виде теста"""

    exercise_type: ExerciseType = ExerciseType.TEST

    questions: list[TestQuestion] = Field(
        default_factory=list,
        min_length=1,
        description="список тестовых вопросов"
    )


class FileUploadExercise(Exercise):
    """Задание с загрузкой файла"""

    exercise_type: ExerciseType = ExerciseType.FILE_UPLOAD

    task: str = Field(..., description="Текст задания, который увидит студент")
    allowed_extensions: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Разрешённые расширения файлов",
        examples=[[".pdf", ".docx"], [".pptx", ".pdf"], [".py"]]
    )
    submission_instructions: str = Field(
        ..., description="Дополнительные инструкции по оформлению работы"
    )


class GitHubExercise(Exercise):
    """Задание выполняющиеся в GitHub репозитории"""

    repository_task: str = Field(
        ..., description="Задание, которое нужно выполнить в репозитории"
    )
    repository_rules: str = Field(..., description="Правила оформления репозитория")
    required_branch: str = Field(default="main", description="Требуемая ветка для проверки")


class ContentBlock(ABC, BaseModel):
    """Универсальные блоки с контентом"""

    content_type: ContentType
    ai_generated: bool = Field(default=True)


AnyContentBlock = TypeVar("AnyContentBlock", bound=ContentBlock)


class TextBlock(ContentBlock):
    content_type: ContentType = ContentType.TEXT
    md_content: str = Field(..., description="Markdown текст теоретического материала")


class VideoBlock(ContentBlock):
    """Блок с видео контентом"""

    content_type: ContentType = ContentType.VIDEO
    url: str = Field(..., description="Ссылка на видео")
    platform: str = Field(
        ..., description="Платформа с которой взято видео", examples=["YouTube", "RuTube"]
    )
    title: str = Field(..., description="Название видео")
    duration_seconds: PositiveInt = Field(..., description="Длительность в секундах")
    key_moments: dict[int, str] = Field(
        default_factory=dict, description="Тайм-коды ключевых моментов (секунда: описание)"
    )
    discussion_questions: list[str] = Field(
        default_factory=list, description="Вопросы для обсуждения"
    )


class CodeBlock(ContentBlock):
    """Пример кода"""

    content_type: ContentType = ContentType.CODE
    language: str = Field(..., description="Язык программирования")
    code: str = Field(..., description="Программный код")
    explanation: str = Field(..., description="Пояснения к коду")


class QuizBlock(ContentBlock):
    """Блок с вопросами для самопроверки"""

    content_type: ContentType = ContentType.QUIZ
    questions: list[tuple[str, str]] = Field(
        default_factory=list,
        description="Список вопросов для самопроверки с ответами",
        examples=[
            [
                ("Здесь должен быть первый вопрос", "Ответ на первый вопрос"),
                ("Здесь должен быть второй вопрос", "Ответ на второй вопрос"),
            ]
        ],
    )


class Assessment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    assessment_type: AssessmentType = Field(..., description="Тип ассессмента")
    title: str = Field(..., description="Название ассессмента")
    verification_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="""Правила проверки и создания ассессмента,
        для генерации индивидуального варианта для каждого студента""",
        examples=[
            {"questions_count": 10, "time_limit": 1800},  # Для теста
            {"programming_language": "C#", "repository_required": True},  # Для кода
            {"min_words": 500, "max_words": 1000},  # Для эссе
        ],
    )
