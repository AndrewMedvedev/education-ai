from uuid import UUID

from pydantic import BaseModel, Field, NonNegativeFloat, NonNegativeInt


class CourseGenerate(BaseModel):
    """DTO для генерации курса"""

    course_id: UUID
    prompt: str


class TestResult(BaseModel):
    """Результаты тестирования"""

    score: NonNegativeFloat = Field(..., ge=0.0, le=100.0, description="Набранные баллы")
    correct_answers_count: NonNegativeInt = Field(..., description="Количество правильных ответов")
    is_passed: bool = Field(default=False, description="Пройдено ли тестирование")
    ai_feedback: str | None = Field(default=None, description="Обратная связь от AI")
