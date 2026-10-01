from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr
from pydantic.alias_generators import to_camel

from src.iam.domain.types import RoleId


class InvitationCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)

    email: EmailStr
    granted_roles: set[RoleId] | None = None
    organization_id: UUID | None = None
