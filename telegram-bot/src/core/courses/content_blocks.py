from abc import ABC
from enum import StrEnum

from pydantic import BaseModel, Field, PositiveInt


class ContentType(StrEnum):
    """Тип контента внутри блока"""

    TEXT = "text"
    VIDEO = "video"
    CODE = "code"
    QUIZ = "quiz"


class ContentBlock(ABC, BaseModel):
    """Универсальные блоки с контентом"""

    content_type: ContentType
    ai_generated: bool = Field(default=True)


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


AnyContentBlock = TextBlock | VideoBlock | CodeBlock | QuizBlock
