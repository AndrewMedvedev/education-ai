from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl
from pydantic.alias_generators import to_camel


class UserResponse(BaseModel):
    """Данные пользователя."""

    id: UUID = Field(description="Идентификатор пользователя.")
    created_at: datetime = Field(description="Дата регистрации.")
    updated_at: datetime = Field(description="Дата последнего обновления.")

    email: EmailStr = Field(description="Email (логин пользователя).")
    username: str | None = Field(
        default=None,
        description="Никнейм пользователя.",
        examples=["ivanov.ii"],
    )
    full_name: str | None = Field(
        default=None,
        description="ФИО пользователя",
        examples=["Иванов Иван Иванович"],
    )
    avatar_url: HttpUrl | None = Field(default=None, description="Ссылка на CDN с аватаркой.")
    is_active: bool = Field(description="Актива ли учётная запись.")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CreateUserDTO(BaseModel):
    """Создание пользователя (приглашение, регистрация, ...)."""

    password: str = Field(description="Пароль пользователя")
    full_name: str | None = Field(
        default=None,
        description="ФИО пользователя",
        examples=["Иванов Иван Иванович"],
    )
    username: str | None = Field(
        default=None,
        description="Никнейм пользователя.",
        examples=["ivan.ivanov"],
    )

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class UpdateUserDTO(BaseModel):
    """Запрос на изменение учётных данных."""

    username: str | None = Field(default=None, description="Новый никнейм.")
    full_name: str | None = Field(default=None, description="Новое ФИО.")
    avatar_url: str | None = Field(default=None, description="Ссылка на аватарку в CDN.")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


@dataclass(frozen=True, slots=True)
class UserQueryParamFilters:
    """Query param фильтры для поиска списка пользователей."""

    email: EmailStr | None = None
    username: str | None = None
    full_name: str | None = None
