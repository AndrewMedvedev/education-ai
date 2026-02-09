from pydantic import BaseModel, Field, NonNegativeInt


class AssignmentResult(BaseModel):
    """Результат выполнения практического задания"""

    score: NonNegativeInt = Field(..., description="Набранные баллы")
    is_passing: bool = Field(default=False, description="Пройдено ли задание")
