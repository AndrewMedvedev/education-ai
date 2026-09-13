from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field


class CreateServiceAccountDTO(BaseModel):
    """Создание сервисного аккаунта."""

    name: str = Field(
        min_length=1,
        max_length=255,
        description="Имя сервисного аккаунта.",
        examples=["Tasks Service"],
    )
    description: str | None = Field(default=None, description="Описание.")
    organization_id: UUID = Field(description="Идентификатор организации.")
    roles: set[UUID] = Field(default_factory=set, description="Роли назначенный аккаунту.")


class UpdateServiceAccountDTO(BaseModel):
    """Обновление сервисного аккаунта."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Имя сервисного аккаунта.",
        examples=["Tasks Service"],
    )
    description: str | None = Field(default=None, description="Описание.")
    roles: set[UUID] | None = Field(
        default=None,
        description="Новый список ролей (перезапишет старый).",
    )


class ServiceAccountResponse(BaseModel):
    """Схема ответа для сервисного аккаунта."""

    id: UUID = Field(description="Системный уникальный идентификатор.")
    created_at: AwareDatetime = Field(description="Дата создания.")
    updated_at: AwareDatetime = Field(description="Дата последнего обновления.")

    name: str = Field(description="Имя сервисного аккаунта.", examples=["Tasks Service"])
    client_id: str = Field(description="Публичный уникальный идентификатор.")
    description: str | None = Field(default=None, description="Описание.")
    organization_id: UUID = Field(description="Идентификатор организации.")
    roles: set[UUID] = Field(description="Роли назначенный аккаунту.")
    is_active: bool = Field(description="Активен ли аккаунт.")


class ClientCredentials(BaseModel):
    """Учётные данные для сервисного аккаунта."""

    id: UUID = Field(description="Уникальный системный идентификатор.")
    created_at: AwareDatetime = Field(description="Дата создания.")

    client_id: str = Field(description="Публичный уникальный идентификатор.")
    client_secret: str = Field(
        description="Секрет сервисного аккаунта. Возвращается только один раз при создании.",
    )

    is_active: bool = Field(description="Активен ли аккаунт.")
