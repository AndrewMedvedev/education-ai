from uuid import UUID

from sqlalchemy import Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.shared.infra.database.types import DatetimeNull, DatetimeTz, StrUnique


class OrganizationOrm(Base):
    __tablename__ = "organizations"

    name: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str]
    is_active: Mapped[bool]


class InvitationOrm(Base):
    __tablename__ = "organization_invitations"

    email: Mapped[str]
    user_id: Mapped[UUID | None] = mapped_column(nullable=True)
    token: Mapped[StrUnique]
    invited_by: Mapped[UUID]
    granted_roles: Mapped[list[UUID]] = mapped_column(JSONB)
    organization_id: Mapped[UUID]
    expires_at: Mapped[DatetimeTz]

    used_at: Mapped[DatetimeNull]
    is_used: Mapped[bool]

    __table_args__ = (
        Index("ix_organization_invitations_organization_used", "organization_id", "is_used"),
    )
