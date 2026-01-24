from __future__ import annotations

from typing import Any, Self

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
from .enums import AssessmentType, BlockType, UserRole


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


class CourseTask(BaseModel):
    user_id: PositiveInt
    title: str
    file_ids: list[str] = Field(default_factory=list)


class Course(BaseModel):
    """Модель образовательного курса"""

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=current_datetime)
    creator_id: PositiveInt = Field(..., description="Telegram ID пользователя")
    title: str = Field(
        ...,
        description="Понятное название курса",
        examples=["Разработка веб-приложений на Python с использованием Django"]
    )
    description: str = Field(..., description="Общее описание и введение в курс")
    modules: list[Module]


class Module(BaseModel):
    id: UUID = Field(default_factory=uuid4, description="Не указывать, генерируется автоматически")
    title: str = Field(..., description="Название модуля")
    description: str = Field(
        ..., description="Краткий обзор тем и технологий с которыми ознакомится студент"
    )
    order: NonNegativeInt = Field(..., description="Порядковый номер модуля")
    content_blocks: list[ContentBlock] = Field(
        default_factory=list,
        description="Вместо жесткой структуры — LEGO-подобные блоки"
    )
    assessments: list[Assessment] = Field(
        default_factory=list, description="Ассессменты для проверки знаний"
    )


class TheoryBlock(BaseModel):
    """Теоретический блок"""

    md_content: str = Field(..., description="Markdown текст")
    generated_by_ai: bool = Field(default=True)


class VideoBlock(BaseModel):
    """Блок с видео контентом"""

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


class CodeExampleBlock(BaseModel):
    """Пример кода"""

    language: str = Field(..., description="Язык программирования")
    code: str = Field(..., description="Программный код")
    explanation: str = Field(..., description="Пояснения к коду")


class ReadingBlock(BaseModel):
    """Материал для чтения"""

    title: str = Field(..., description="Название материала")
    source_type: str = Field(..., description="Тип (книга, статья, исследование)")
    pages: str | None = Field(default=None, description="", examples=["10-25"])
    url: str | None = Field(default=None, description="Ссылка на материал")
    reading_time_minutes: PositiveInt = Field(..., description="Примерное время чтения")


AnyBlockData = TheoryBlock | VideoBlock | CodeExampleBlock | ReadingBlock


class ContentBlock(BaseModel):
    """Универсальные блоки с контентом (LEGO-подобные блоки).

    Примеры data для разных типов:
     - type="text": {"content": "Markdown текст", "generated_by_ai": true}
     - type="video": {"url": "youtube.com/...", "platform": "youtube"}
     - type="code_example": {"language": "python", "code": "print('hello')", "explanation": "..."}
     - type="reading": {"title": "Книга", "pages": "10-25", "link": "..."}
    """

    id: UUID = Field(default_factory=uuid4, description="Не указывать, генерируется автоматически")
    block_type: BlockType = Field(
        ..., description="Тип контент блока (строго из доступных enum)"
    )
    data: AnyBlockData = Field(
        ...,
        description="""Примеры data для разных типов:
        - block_type="text": {"md_content": "Markdown текст", "generated_by_ai": true}
        - block_type="video": {"url": "youtube.com/...", "platform": "youtube"}
        - block_type="code_example": {"language": "python", "code": "print('hello')", "explanation": "..."}
        - block_type="reading": {"title": "Книга", "pages": "10-25", "link": "..."}
        """  # noqa: E501
    )


class Assessment(BaseModel):
    id: UUID = Field(default_factory=uuid4, description="Не указывать, генерируется автоматически")
    assessment_type: AssessmentType = Field(..., description="Тип ассессмента")
    title: str = Field(..., description="Название ассессмента")
    description: str = Field(..., description="Краткое описание (1-2 предложения)")
    verification_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Правила проверки и создания ассессмента",
        examples=[
            {"question_count": 10, "time_limit": 1800},  # Для теста
            {"programming_language": "C#", "repository_required": True},  # Для кода
            {"min_words": 500, "max_words": 1000},  # Для эссе
        ],
    )
