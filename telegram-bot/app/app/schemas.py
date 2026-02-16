from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PositiveInt, SecretStr

from app.core.entities.user import UserRole


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
    email: EmailStr
    role: UserRole


class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: UserRole


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    email: EmailStr
    role: UserRole
    is_active: bool = False


class Credentials(BaseModel):
    email: EmailStr
    password: str


class CourseGenerate(BaseModel):
    """DTO для генерации курса"""

    course_id: UUID
    prompt: str
