from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, PositiveInt, SecretStr

from src.utils import current_datetime


class Student(BaseModel):
    """Студент - пользователь, который проходит курс"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=current_datetime)
    user_id: PositiveInt | None = None
    course_id: UUID
    invited_by: PositiveInt
    full_name: str
    login: str
    password_hash: SecretStr
    is_active: bool = False


class StudentProgress(BaseModel):
    """Прогресс студента на курсе"""

    model_config = ConfigDict(from_attributes=True)

    course_id: UUID
    user_id: UUID
    started_at: datetime
    completed_at: datetime | None = None
    current_module_id: UUID
    overall_percentage: NonNegativeFloat = Field(default=0.0)
