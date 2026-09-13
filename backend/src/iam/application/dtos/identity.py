from dataclasses import dataclass, field
from enum import IntEnum, auto
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.iam.domain.vo import Email


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
