from typing import Self

from datetime import datetime
from enum import StrEnum

from aiogram.types import CallbackQuery, Message
from pydantic import BaseModel, ConfigDict, Field

from src.utils import current_datetime


class UserRole(StrEnum):
    """Возможные роли пользователя"""

    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class User(BaseModel):
    """Модель пользователя Telegram бота"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime = Field(default_factory=current_datetime)
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    role: UserRole

    @classmethod
    def from_message(cls, message: Message | CallbackQuery, role: UserRole) -> Self:
        """Фабричный метод для создания пользователя, используя его сообщение"""

        return cls(
            id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            role=role,
        )
