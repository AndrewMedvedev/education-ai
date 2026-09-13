import logging
from importlib import import_module

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import session_factory
from src.core.settings import super_admin_config
from src.iam.domain.entities import Membership, Permission, Role, User
from src.iam.domain.permissions.registry import get_permissions
from src.iam.domain.types import RoleId
from src.iam.domain.vo import (
    Email,
    FullName,
    PermissionGrant,
    PermissionScope,
    SecretHash,
    Username,
)
from src.iam.infra.database.repos.membership import SqlMembershipRepository
from src.iam.infra.database.repos.permission import SqlPermissionRepository
from src.iam.infra.database.repos.role import SqlRoleRepository
from src.iam.infra.database.repos.user import SqlUserRepository
from src.iam.security import hash_password
from src.organization.domain.entities import Organization
from src.organization.infra.repos import SqlOrganizationRepository

logger = logging.getLogger(__name__)

ADMIN_ROLE_CODE = "admin"
USER_ROLE_CODE = "user"
SYSTEM_PERMISSION_MODULES = (
    "src.iam.domain.permissions.permissions",
    "src.iam.domain.permissions.users",
    "src.organization.domain.permissions.organizations",
    "src.courses.domain.permissions.courses",
    "src.courses.domain.permissions.theory_session",
    "src.llm_router.domain.permissions.ai_models",
)


def _load_system_permission_modules() -> None:
    for module in SYSTEM_PERMISSION_MODULES:
        import_module(module)


def _build_admin_user(admin_email: Email) -> User:
    return User(
        email=admin_email,
        username=Username("admin"),
        full_name=FullName("System Admin"),
        password_hash=SecretHash(hash_password(super_admin_config.password)),
    )


def _build_user(user_email: Email) -> User:
    return User(
        email=user_email,
        username=Username("user"),
        full_name=FullName("little user"),
        password_hash=SecretHash(hash_password("12345")),
    )


async def _get_or_create_user_role(session: AsyncSession) -> Role:
    _load_system_permission_modules()
    role_repo = SqlRoleRepository(session)

    if role := await role_repo.get_by_code(USER_ROLE_CODE):
        return role

    role = Role(
        name="User",
        code=USER_ROLE_CODE,
        description="Built-in role with user system permissions.",
        permissions={
            PermissionGrant(permission=data["permission"], scope=PermissionScope(data["scope"]))
            for data in [
                {"scope": "own", "permission": "permissions.read"},
                {"scope": "own", "permission": "course.read"},
                {"scope": "course", "permission": "course.course_read"},
                {"scope": "object", "permission": "course.read"},
                {"scope": "own", "permission": "users.update"},
                {"scope": "course", "permission": "course.read"},
                {"scope": "organization", "permission": "course.read"},
            ]
        },
        is_default=True,
    )
    await role_repo.create(role)
    logger.info("User role created successfully")
    return role


async def _get_or_create_admin_role(session: AsyncSession) -> Role:
    _load_system_permission_modules()
    role_repo = SqlRoleRepository(session)

    if role := await role_repo.get_by_code(ADMIN_ROLE_CODE):
        return role

    role = Role(
        name="System administrator",
        code=ADMIN_ROLE_CODE,
        description="Built-in role with all system permissions.",
        permissions={
            PermissionGrant(permission=permission.code, scope=scope)
            for permission in get_permissions()
            for scope in permission.scopes
        },
        is_default=True,
    )
    await role_repo.create(role)
    logger.info("Admin role created successfully")
    return role


async def create_permissions() -> None:
    """Создание системных разрешений"""
    _load_system_permission_modules()

    async with session_factory() as session:
        repo = SqlPermissionRepository(session)

        for perm in get_permissions():
            entity = Permission(
                resource=perm.resource,
                action=perm.action,
                title=perm.title,
                description=perm.description,
                scopes=perm.scopes,
            )
            await repo.create_or_update(entity)

        await session.commit()
        logger.info("Permissions created successfully")


async def create_first_admin() -> None:
    """Создание системного администратора"""

    async with session_factory() as session:
        user_repo = SqlUserRepository(session)
        admin_email = Email(super_admin_config.email)

        exists = await user_repo.get_by_email(admin_email)
        if exists:
            logger.info("Admin already exists")
            return

        admin = _build_admin_user(admin_email)
        await user_repo.create(admin)
        await session.commit()
        logger.info("First admin created successfully")


async def create_user_admin() -> None:
    """Создание системного администратора"""

    async with session_factory() as session:
        user_repo = SqlUserRepository(session)
        user_email = Email("user@user.com")

        exists = await user_repo.get_by_email(user_email)
        if exists:
            logger.info("User already exists")
            return

        user = _build_user(user_email)
        await user_repo.create(user)
        await session.commit()
        logger.info("First user created successfully")


async def create_default_organization() -> None:
    """Создание системной организации и назначение первого администратора."""

    async with session_factory() as session:
        user_repo = SqlUserRepository(session)
        organization_repo = SqlOrganizationRepository(session)
        membership_repo = SqlMembershipRepository(session)

        admin_email = Email(super_admin_config.email)
        user_email = Email("user@user.com")

        admin = await user_repo.get_by_email(admin_email)
        user = await user_repo.get_by_email(user_email)
        if admin is None:
            admin = _build_admin_user(admin_email)
            await user_repo.create(admin)
            logger.info("First admin created successfully")
        if user is None:
            user = _build_user(user_email)
            await user_repo.create(user)
            logger.info("First admin created successfully")

        organization = await organization_repo.get_by_email(super_admin_config.email)
        if organization is None:
            organization = Organization(
                name="Master Organization",
                email=super_admin_config.email,
                description="Default system organization.",
            )
            await organization_repo.create(organization)
            logger.info("Default organization created successfully")

        admin_role = await _get_or_create_admin_role(session)
        user_role = await _get_or_create_user_role(session)

        membership_admin = await membership_repo.get_by_user_and_organization(
            admin.id,
            organization.id,
        )
        membership_user = await membership_repo.get_by_user_and_organization(
            user.id,
            organization.id,
        )
        if membership_admin:
            logger.info("Admin membership already exists")
        else:
            await membership_repo.create(
                Membership(
                    user_id=admin.id,
                    organization_id=organization.id,
                    roles={RoleId(admin_role.id)},
                )
            )

        if membership_user:
            logger.info("User membership already exists")
        else:
            await membership_repo.create(
                Membership(
                    user_id=user.id,
                    organization_id=organization.id,
                    roles={RoleId(user_role.id)},
                )
            )

        await session.commit()
        logger.info("First admin assigned to default organization successfully")
