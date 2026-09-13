from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, PositiveInt

from src.organization.application.dtos import OrganizationRef


class UserCredentials(BaseModel):
    """Учётные данные пользователя."""

    email: EmailStr = Field(description="Логин пользователя")
    password: str = Field(description="Пароль пользователя")


class MembershipResponse(BaseModel):
    """Ссылка на организацию в которой состоит пользователь."""

    id: UUID = Field(description="Уникальный идентификатор участника")
    joined_at: datetime = Field(description="Дата присоединения к организации")
    organization: OrganizationRef = Field(description="Организация в которой состоит пользователь")


class LoginResponse(BaseModel):
    """Результат аутентификации."""

    authentication_token: str = Field(description="Короткоживущий токен 1-2 минуты")
    memberships: list[MembershipResponse] = Field(
        default_factory=list,
        description="Организации в которых состоит пользователь",
    )


class TokenRequest(BaseModel):
    """Запрос для получения пары токенов."""

    authentication_token: str = Field(description="Токен полученный от - POST /auth/login")
    membership_id: UUID = Field(description="ID учётной записи для организации")


class TokensResponse(BaseModel):
    """Пара токенов access + refresh."""

    access_token: str = Field(description="Основной токен для аутентификации (живёт 15-30 минут)")
    refresh_token: str = Field(description="Для получения новой пары (хранить в secure storage)")
    token_type: str = Field(default="Bearer", frozen=True)
    expires_at: PositiveInt = Field(
        description="Время истечения access токена в формате timestamp",
    )


class LogoutRequest(BaseModel):
    """Запрос для выхода из учётной записи."""

    access_token: str = Field(description="Основной токен для аутентификации (живёт 15-30 минут)")
    refresh_token: str = Field(description="Долгоживущий токен")
