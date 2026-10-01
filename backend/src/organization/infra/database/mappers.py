from uuid import UUID

from src.iam.domain.types import RoleId
from src.organization.domain.entities import Invitation, Organization
from src.shared.domain.vo import Email
from src.shared.infra.database.repos.sqlalchemy import ModelMapper

from .models import InvitationOrm, OrganizationOrm


class OrganizationMapper(ModelMapper[Organization, OrganizationOrm]):
    @staticmethod
    def from_model(model: OrganizationOrm) -> Organization:
        return Organization(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            name=model.name,
            email=model.email,
            description=model.description,
            is_active=model.is_active,
        )

    @staticmethod
    def to_model(entity: Organization) -> OrganizationOrm:
        return OrganizationOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            name=entity.name,
            email=entity.email,
            description=entity.description,
            is_active=entity.is_active,
        )


class InvitationMapper(ModelMapper[Invitation, InvitationOrm]):
    @staticmethod
    def from_model(model: InvitationOrm) -> Invitation:
        return Invitation(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            email=Email(model.email),
            user_id=model.user_id,
            token=model.token,
            invited_by=model.invited_by,
            granted_roles={RoleId(UUID(str(role_id))) for role_id in model.granted_roles}
            if model.granted_roles
            else set(),
            organization_id=model.organization_id,
            expires_at=model.expires_at,
            used_at=model.used_at,
            is_used=model.is_used,
        )

    @staticmethod
    def to_model(invitation: Invitation) -> InvitationOrm:
        return InvitationOrm(
            id=invitation.id,
            created_at=invitation.created_at,
            updated_at=invitation.updated_at,
            deleted_at=invitation.deleted_at,
            email=invitation.email.value,
            user_id=invitation.user_id,
            token=invitation.token,
            invited_by=invitation.invited_by,
            granted_roles=[str(role_id) for role_id in invitation.granted_roles],
            organization_id=invitation.organization_id,
            expires_at=invitation.expires_at,
            used_at=invitation.used_at,
            is_used=invitation.is_used,
        )
