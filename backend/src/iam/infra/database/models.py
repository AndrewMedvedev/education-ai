from typing import Any

from uuid import UUID

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.shared.infra.database.types import (
    DatatimeTz,
    DatetimeNull,
    StrNull,
    StrUnique,
    TextNull,
)


class UserOrm(Base):
    __tablename__ = "users"

    email: Mapped[StrUnique]
    username: Mapped[StrNull]
    full_name: Mapped[StrNull]
    avatar_url: Mapped[StrNull]
    password_hash: Mapped[StrUnique]
    is_active: Mapped[bool]

    memberships: Mapped[list["MembershipOrm"]] = relationship(back_populates="user")

    __table_args__ = (
        Index("ix_users_is_active", "is_active"),
    )


class ServiceAccountOrm(Base):
    __tablename__ = "service_accounts"

    name: Mapped[str]
    description: Mapped[TextNull]

    client_id: Mapped[StrUnique]
    client_secret_hash: Mapped[str]

    organization_id: Mapped[UUID]
    roles: Mapped[list[UUID]] = mapped_column(JSONB)
    is_active: Mapped[bool]

    __table_args__ = (
        Index(
            "ix_service_accounts_organization_active",
            "organization_id",
            "is_active",
        ),
    )


class MembershipOrm(Base):
    __tablename__ = "memberships"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=False)
    organization_id: Mapped[UUID]
    roles: Mapped[list[UUID]] = mapped_column(JSONB)
    expires_at: Mapped[DatetimeNull]
    is_active: Mapped[bool]

    user: Mapped["UserOrm"] = relationship(back_populates="memberships")

    __table_args__ = (
        Index("ix_memberships_organization_id", "organization_id"),
        UniqueConstraint("user_id", "organization_id", name="uq_memberships_user_organization"),
    )


class PermissionOrm(Base):
    __tablename__ = "permissions"

    resource: Mapped[str]
    action: Mapped[str]

    title: Mapped[str]
    description: Mapped[TextNull]

    scopes: Mapped[list[str]] = mapped_column(JSONB)

    __table_args__ = (UniqueConstraint("resource", "action", name="uq_resource_action"),)


class RoleOrm(Base):
    __tablename__ = "roles"

    name: Mapped[str]
    code: Mapped[StrUnique]
    description: Mapped[TextNull]

    permissions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    is_default: Mapped[bool]

    author_id: Mapped[UUID | None] = mapped_column(nullable=True)
    organization_id: Mapped[UUID | None] = mapped_column(nullable=True)


class InvitationOrm(Base):
    __tablename__ = "invitations"

    email: Mapped[str]
    token: Mapped[StrUnique]
    invited_by: Mapped[UUID]

    granted_roles: Mapped[list[UUID]] = mapped_column(JSONB)
    organization_id: Mapped[UUID]
    expires_at: Mapped[DatatimeTz]

    used_at: Mapped[DatetimeNull]
    is_used: Mapped[bool]

    __table_args__ = (
        Index("ix_invitations_organization_used", "organization_id", "is_used"),
    )
