from pydantic import BaseModel, NonNegativeFloat


class TestResult(BaseModel):
    score: NonNegativeFloat
    is_passing: bool = False
    ai_feedback: str | None = None
