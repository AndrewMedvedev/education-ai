from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

from ..commons import current_datetime


class UserRole(StrEnum):
    """Возможные роли пользователя"""

    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class User(BaseModel):
    """Модель пользователя Telegram бота"""

    model_config = ConfigDict(from_attributes=True)

    id: PositiveInt
    created_at: datetime = Field(default_factory=current_datetime)
    username: str | None = None
    role: UserRole
