from uuid import UUID

from src.iam.domain.entities import Invitation, Membership, Permission, Role, ServiceAccount, User
from src.iam.domain.vo import (
    Email,
    FullName,
    PermissionGrant,
    PermissionScope,
    SecretHash,
    Username,
)
from src.shared.infra.database import ModelMapper

from ...domain.types import RoleId
from .models import (
    InvitationOrm,
    MembershipOrm,
    PermissionOrm,
    RoleOrm,
    ServiceAccountOrm,
    UserOrm,
)


class UserMapper(ModelMapper[User, UserOrm]):
    @staticmethod
    def from_model(model: UserOrm) -> User:
        return User(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            email=Email(model.email),
            username=Username(model.username),
            full_name=FullName(model.full_name),
            avatar_url=model.avatar_url,
            password_hash=SecretHash(model.password_hash),
            is_active=model.is_active,
        )

    @staticmethod
    def to_model(entity: User) -> UserOrm:
        return UserOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            email=entity.email.value,
            username=entity.username.value,
            full_name=entity.full_name.value,
            avatar_url=entity.avatar_url,
            password_hash=entity.password_hash.get_hashed_value(),
            is_active=entity.is_active,
        )


class ServiceAccountMapper(ModelMapper[ServiceAccount, ServiceAccountOrm]):
    @staticmethod
    def from_model(model: ServiceAccountOrm) -> ServiceAccount:
        return ServiceAccount(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            name=model.name,
            description=model.description,
            client_id=model.client_id,
            client_secret_hash=SecretHash(model.client_secret_hash),
            organization_id=model.organization_id,
            roles={RoleId(UUID(str(role_id))) for role_id in model.roles},
            is_active=model.is_active,
        )

    @staticmethod
    def to_model(service_account: ServiceAccount) -> ServiceAccountOrm:
        return ServiceAccountOrm(
            id=service_account.id,
            created_at=service_account.created_at,
            updated_at=service_account.updated_at,
            deleted_at=service_account.deleted_at,
            name=service_account.name,
            description=service_account.description,
            client_id=service_account.client_id,
            client_secret_hash=service_account.client_secret_hash.get_hashed_value(),
            organization_id=service_account.organization_id,
            roles=[str(role_id) for role_id in service_account.roles],
            is_active=service_account.is_active,
        )


class MembershipMapper(ModelMapper[Membership, MembershipOrm]):
    @staticmethod
    def from_model(model: MembershipOrm) -> Membership:
        return Membership(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            user_id=model.user_id,
            organization_id=model.organization_id,
            roles={RoleId(UUID(str(role_id))) for role_id in model.roles},
            expires_at=model.expires_at,
            is_active=model.is_active,
        )

    @staticmethod
    def to_model(membership: Membership) -> MembershipOrm:
        return MembershipOrm(
            id=membership.id,
            created_at=membership.created_at,
            updated_at=membership.updated_at,
            deleted_at=membership.deleted_at,
            user_id=membership.user_id,
            organization_id=membership.organization_id,
            roles=[str(role_id) for role_id in membership.roles],
            expires_at=membership.expires_at,
            is_active=membership.is_active,
        )


class PermissionMapper(ModelMapper[Permission, PermissionOrm]):
    @staticmethod
    def from_model(model: PermissionOrm) -> Permission:
        return Permission(
            resource=model.resource,
            action=model.action,
            title=model.title,
            description=model.description,
            scopes=frozenset(PermissionScope(scope) for scope in model.scopes),
        )

    @staticmethod
    def to_model(permission: Permission) -> PermissionOrm:
        return PermissionOrm(
            resource=permission.resource,
            action=permission.action,
            title=permission.title,
            description=permission.description,
            scopes=list(map(str, permission.scopes)),
        )

    @staticmethod
    def to_dict(permission: Permission) -> dict[str, str | list[str] | None]:
        return {
            "resource": permission.resource,
            "action": permission.action,
            "title": permission.title,
            "description": permission.description,
            "scopes": list(map(str, permission.scopes)),
        }


class RoleMapper(ModelMapper[Role, RoleOrm]):
    @staticmethod
    def from_model(model: RoleOrm) -> Role:
        return Role(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            name=model.name,
            code=model.code,
            description=model.description,
            permissions={
                PermissionGrant(
                    permission=grant["permission"],
                    scope=PermissionScope(grant["scope"]),
                )
                for grant in model.permissions
            },
            is_default=model.is_default,
            author_id=model.author_id,
            organization_id=model.organization_id,
        )

    @staticmethod
    def to_model(role: Role) -> RoleOrm:
        return RoleOrm(
            id=role.id,
            created_at=role.created_at,
            updated_at=role.updated_at,
            deleted_at=role.deleted_at,
            name=role.name,
            code=role.code,
            description=role.description,
            permissions=[
                {"permission": grant.permission, "scope": grant.scope.value}
                for grant in role.permissions
            ],
            is_default=role.is_default,
            author_id=role.author_id,
            organization_id=role.organization_id,
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
            token=model.token,
            invited_by=model.invited_by,
            granted_roles=set(model.granted_roles),
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
            token=invitation.token,
            invited_by=invitation.invited_by,
            granted_roles=list(invitation.granted_roles),
            organization_id=invitation.organization_id,
            expires_at=invitation.expires_at,
            used_at=invitation.used_at,
            is_used=invitation.is_used,
        )
