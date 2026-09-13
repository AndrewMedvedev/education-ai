from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.iam.domain.vo import PermissionGrant, PermissionScope
from src.shared.application.dtos import BaseQueryParamFilters


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
