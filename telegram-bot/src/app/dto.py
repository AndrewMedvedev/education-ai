from pydantic import BaseModel, NonNegativeFloat, NonNegativeInt


class TestResult(BaseModel):
    """Результаты тестирования"""

    score: NonNegativeFloat
    correct_answers_count: NonNegativeInt
    is_passed: bool = False
    ai_feedback: str | None = None
