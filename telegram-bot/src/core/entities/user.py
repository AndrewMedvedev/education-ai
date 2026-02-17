from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, SecretStr

from ..commons import current_datetime


class UserRole(StrEnum):
    """Возможные роли пользователя"""

    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PositiveInt
    created_at: datetime = Field(default_factory=current_datetime)
    username: str | None
    role: UserRole


class Student(User):
    role: UserRole = UserRole.STUDENT

    group_id: UUID
    full_name: str


class Teacher(User):
    role: UserRole = UserRole.TEACHER

    password_hash: SecretStr


AnyUser = Student | Teacher
