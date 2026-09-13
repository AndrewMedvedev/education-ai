from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum, auto
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, PositiveInt

from src.iam.domain.vo import Email, PermissionGrant, PermissionScope
from src.organization.application.dtos import OrganizationRef
from src.shared.application.dtos import BaseQueryParamFilters


class IdentityType(IntEnum):
    """Тип субъекта авторизации."""

    USER = auto()
    SERVICE_ACCOUNT = auto()
    AI_AGENT = auto()


@dataclass(frozen=True, slots=True)
class Identity:
    """Субъект авторизации - аутентифицированная сущность выполняющая запрос."""

    id: UUID
    type: IdentityType

    email: Email | None = None
    organization_id: UUID | None = None
    membership_id: UUID | None = None

    roles: frozenset[str] = field(default_factory=frozenset)
    permissions: frozenset[str] = field(default_factory=frozenset)


# =================================================================================================
# Auth Request & Response DTOs
# =================================================================================================


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


# =================================================================================================
# Invitations Request & Response DTOs
# =================================================================================================


class IdentityResponse(BaseModel):
    """Текущий субъект авторизации."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Идентификатор субъекта.")
    type: IdentityType = Field(description="Тип субъекта.")

    email: Email | None = Field(
        None,
        description="Email (логин)",
        examples=["current.identity@mail.com"],
    )
    organization_id: UUID | None = Field(
        None,
        description="Организация в которой состоит субъект.",
    )
    membership_id: UUID | None = Field(None, description="Привязка к организации.")

    roles: set[str] = Field(default_factory=set, description="Системные названия ролей.")
    permissions: set[str] = Field(default_factory=set, description="Список доступных прав.")


# =================================================================================================
# Users Request & Response DTOs
# =================================================================================================


class UserResponse(BaseModel):
    """Данные пользователя."""

    id: UUID = Field(description="Идентификатор пользователя.")
    created_at: datetime = Field(description="Дата регистрации.")
    updated_at: datetime = Field(description="Дата последнего обновления.")

    email: EmailStr = Field(description="Email (логин пользователя).")
    username: str | None = Field(
        None,
        description="Никнейм пользователя.",
        examples=["ivan.ivanov"],
    )
    full_name: str | None = Field(
        None,
        description="ФИО пользователя",
        examples=["Иванов Иван Иванович"],
    )
    avatar_url: HttpUrl | None = Field(None, description="Ссылка на CDN с аватаркой.")
    is_active: bool = Field(description="Актива ли учётная запись.")


class UserCreate(BaseModel):
    """Создание пользователя (приглашение, регистрация, ...)."""

    password: str = Field(description="Пароль пользователя")
    full_name: str | None = Field(
        None,
        description="ФИО пользователя",
        examples=["Иванов Иван Иванович"],
    )
    username: str | None = Field(
        None,
        description="Никнейм пользователя.",
        examples=["ivan.ivanov"],
    )


class UserUpdate(BaseModel):
    """Запрос на изменение учётных данных."""

    username: str | None = Field(None, description="Новый никнейм.")
    full_name: str | None = Field(None, description="Новое ФИО.")
    avatar_url: HttpUrl | None = Field(None, description="Ссылка на аватарку в CDN.")


class UserQueryParamFilters(BaseModel):
    """Query param фильтры для поиска списка пользователей."""

    email: EmailStr | None = None
    username: str | None = None
    full_name: str | None = None


# =================================================================================================
# Roles & Permissions Request & Response DTOs
# =================================================================================================


class PermissionQueryParamFilters(BaseQueryParamFilters):
    """Фильтры для получения списка прав."""

    resource: str | None = None
    action: str | None = None
    scopes: list[PermissionScope] | None = None


class PermissionResponse(BaseModel):
    """Право - действие в системе."""

    model_config = ConfigDict(from_attributes=True, revalidate_instances="always")

    resource: str = Field(description="Ресурс на который выдаётся право.", examples=["task"])
    action: str = Field(
        description="Действие которое можно выполнить над ресурсом.",
        examples=["create", "update"],
    )
    code: str = Field(description="Системный код: resource:action", examples=["task.create"])

    title: str = Field(description="Название права.", examples=["Создать задачу"])
    description: str | None = Field(None, description="Человекочитаемое описание для UI.")

    scopes: set[PermissionScope] = Field(
        default_factory=set,
        description="Области действия доступные для этого права.",
    )


class CreateRoleDTO(BaseModel):
    """Создание новой роли."""

    name: str = Field(
        min_length=1,
        max_length=255,
        description="Человекочитаемое название роли.",
        examples=["Менеджер поддержки", "Разработчик", "HR менеджер"],
    )
    code: str = Field(
        min_length=1,
        max_length=100,
        description="Уникальный системный код роли",
        examples=["support_manager"],
    )
    description: str | None = Field(default=None, description="Описание роли.")
    permissions: set[PermissionGrant] = Field(min_length=1, description="Назначенные разрешения.")


class UpdateRoleDTO(BaseModel):
    """Обновление роли."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Человекочитаемое название роли.",
        examples=["Менеджер поддержки", "Разработчик", "HR менеджер"],
    )
    code: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Уникальный системный код роли",
        examples=["support_manager"],
    )
    description: str | None = Field(default=None, description="Описание роли.")


class RoleResponse(BaseModel):
    """Роль - оперирует набором прав."""

    id: UUID = Field(description="Уникальный идентификатор роли.")
    created_at: datetime = Field(description="Дата создания.")
    updated_at: datetime = Field(description="Дата последнего обновления.")

    name: str = Field(
        description="Человекочитаемое название роли.",
        examples=["Системный администратор", "HR Manager", "Developer"],
    )
    code: str = Field(
        description="Уникальное системное название.",
        examples=["admin", "support_agent"],
    )
    description: str | None = Field(None, description="Описание возможностей.")

    permissions: set[PermissionGrant] = Field(description="Список прав назначенных этой роли.")
    is_default: bool = Field(
        description="Является ли роль системной (системные роли нельзя изменять).",
    )
