from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

from src.iam.domain.types import RoleId


class OrganizationRef(BaseModel):
    """Ссылка на организацию."""

    id: UUID = Field(description="Уникальный идентификатор организации")
    name: str = Field(description="Наименование организации", examples=["Microsoft"])


class OrganizationCreate(BaseModel):
    name: str = Field(
        max_length=255,
        description="Наименование организации",
        examples=["Microsoft"],
    )
    email: EmailStr = Field(description="Адрес электронной почты")
    description: str = Field(description="Описание компании")


class OrganizationEdit(BaseModel):
    """
    Редактирование информации о контрагенте
    """

    name: str | None = Field(None, max_length=255, description="Наименование")
    email: EmailStr | None = Field(None, description="Адрес электронной почты")
    description: str | None = Field(None, description="Описание компании")


class InvitationCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)

    email: EmailStr
    granted_roles: set[RoleId]
    organization_id: UUID
