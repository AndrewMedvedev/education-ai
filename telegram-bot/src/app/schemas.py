from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PositiveInt

from src.core.entities.user import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = Field(default="Bearer", frozen=True)
    expires_at: PositiveInt


class TokensPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = Field(default="Bearer", frozen=True)
    expires_at: PositiveInt


class CurrentUser(BaseModel):
    """Текущий пользователь"""

    user_id: UUID
    username: str
    email: EmailStr
    role: UserRole


class UserRegister(BaseModel):
    username: str
    full_name: str
    email: EmailStr
    password: str
    role: UserRole


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    username: str
    full_name: str
    email: EmailStr
    role: UserRole
    is_active: bool = False


class CourseGenerate(BaseModel):
    """DTO для генерации курса"""

    course_id: UUID
    prompt: str
