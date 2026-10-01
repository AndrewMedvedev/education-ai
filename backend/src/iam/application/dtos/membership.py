from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.iam.domain.types import RoleId


class CreateMembershipDTO(BaseModel):
    """Создание пользователя (приглашение, регистрация, ...)."""

    user_id: UUID = Field(description="Идентификатор пользователя.")
    organization_id: UUID = Field(description="Идентификатор организации.")
    roles: set[RoleId] = Field(description="Роль пользователя в организации.")
    expires_at: datetime | None = Field(default=None, description="Дата истечения срока действия.")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
