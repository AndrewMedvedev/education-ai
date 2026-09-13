from __future__ import annotations

from typing import Literal

from abc import ABC
from uuid import UUID

from aiohttp import ClientSession
from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, NonNegativeInt, PositiveInt
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.vo import TestType


class RuntimeContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    aio_session: ClientSession | None = None
    db_session: AsyncSession | None = None


class CourseContext(BaseModel):
    """Контекст курса"""

    course_id: UUID


class Context(CourseContext):
    """Контекст для работы с  курсом"""

    user_id: UUID
    prompt: str


class Knowledge(BaseModel):
    """Знания полученные в ходе создания образовательного курса"""

    course_id: str = Field(..., description="ID курса")
    category: Literal["data", "web_research", "theory"] = Field(
        default="web_research",
        description="""\
        Тип знаний:
         - data - информация полученная из материалов преподавателя
         - web_research - информация полученная в ходе изучения предметной области
         - theory - теоретический материал уже созданного курса
        """,
    )
    source: str = Field(
        ...,
        description="Источник полученных знаний, например имя файла, URL адрес, название ресурса",
    )
    text: str = Field(..., description="Полезная информация, которую необходимо запомнить")
    score: NonNegativeFloat = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Насколько полезна информация, где 1 максимально релевантная информация",
    )


class UserContext(BaseModel):
    """Контекстная информация пользователя"""

    user_id: PositiveInt


class StudentContext(CourseContext, UserContext):
    """Контекстная информация студента для взаимодействия с чат-ботом"""


PASSING_TEST_SCORE = 61


class PracticeResult(BaseModel):
    score: NonNegativeFloat = Field(..., ge=0.0, le=100.0)
    ai_feedback: str | None = None

    @property
    def is_passed(self) -> bool:
        """Выполняет действие `is_passed`, чтобы поддержать основной сценарий модуля."""
        return self.score >= PASSING_TEST_SCORE


class DetailedAnswerQuestion(BaseModel):
    """Вопрос с развёрнутым ответом"""

    text: str = Field(description="Сформулированный вопрос")
    excepted_answer: str = Field(description="Пример правильного ответа на поставленный вопрос")
    hint: str | None = Field(default=None, description="Подсказка (если нужно)")
    points: PositiveInt = Field(
        default=1, description="Количество баллов полученное за правильный ответ"
    )


class MultipleChoiceQuestion(BaseModel):
    """Вопрос с выбором вариантов ответа"""

    text: str = Field(max_length=600, description="Сформулированный вопрос")
    options: list[str] = Field(..., min_length=2, description="Варианты ответа")
    correct_answer: NonNegativeInt = Field(description="Индекс правильного ответа")
    points: PositiveInt = Field(
        default=1, description="Количество баллов полученное за правильный ответ"
    )


class KnowledgeTest(ABC, BaseModel):
    """Тестирования для проверки знаний"""

    test_type: TestType
    title: str = Field(description="Название тестирование")
    estimated_time_minutes: PositiveInt = Field(
        description="Примерное время в минутах за которое можно выполнить тестирование"
    )
    questions: list[MultipleChoiceQuestion | DetailedAnswerQuestion]


class MultipleChoiceTest(KnowledgeTest):
    """Тестирование с выбором варианта ответа"""

    test_type: TestType = TestType.MULTIPLE_CHOICE
    questions: list[MultipleChoiceQuestion] = Field(
        ..., min_length=10, max_length=30, description="Вопросы с выбором варианта ответа"
    )


class DetailedAnswerTest(KnowledgeTest):
    """Тестирование с развёрнутым вариантом ответа"""

    test_type: TestType = TestType.DETAILED_ANSWER
    questions: list[DetailedAnswerQuestion] = Field(
        ..., min_length=5, max_length=15, description="Вопросы с развёрнутым ответом"
    )


AnyKnowledgeTest = DetailedAnswerTest | MultipleChoiceTest
