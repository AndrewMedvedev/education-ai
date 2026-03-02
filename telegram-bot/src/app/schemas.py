from uuid import UUID

from pydantic import BaseModel, Field, NonNegativeFloat, NonNegativeInt, PositiveInt

from ..core.entities.student import PASSING_TEST_SCORE


class CourseGenerate(BaseModel):
    """DTO для генерации курса"""

    course_id: UUID
    prompt: str


class TestResult(BaseModel):
    """Результаты тестирования"""

    score: NonNegativeFloat = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Общая сумма набранных баллов (сумма баллов по всем вопросам), максимум 100"
    )
    correct_answers_count: NonNegativeInt = Field(
        ..., description="Количество правильных ответов (те ответы, которые имеют не нулевой балл)"
    )
    ai_feedback: str | None = Field(
        default=None,
        description="""\
        Краткая обратная связь: можно отметить сильные стороны, указать на типичные ошибки,
        дать рекомендации. (опционально)
        """,
    )

    @property
    def is_passed(self) -> bool:
        """Пройдено ли тестирование"""

        return self.score >= PASSING_TEST_SCORE


class AssignmentResult(BaseModel):
    """Результаты выполнения практического задания"""

    score: NonNegativeFloat = Field(..., ge=0.0, le=100.0, description="Набранные баллы")
    ai_feedback: str | None = Field(
        default=None,
        description="""\
        Краткая обратная связь: можно отметить сильные стороны, указать на типичные ошибки,
        дать рекомендации. (опционально)
        """,
    )


class Leader(BaseModel):
    """Член доски лидеров"""

    user_id: PositiveInt
    full_name: str
    username: str | None = None
    total_score: NonNegativeFloat
    rank: PositiveInt
