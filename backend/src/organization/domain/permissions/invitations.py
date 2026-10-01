from src.iam.domain.entities import Permission
from src.iam.domain.permissions.registry import register_permission
from src.iam.domain.vo import PermissionScope

INVITE = register_permission(
    Permission(
        resource="organization-invitations",
        action="invite",
        scopes=frozenset(
            {
                PermissionScope.GLOBAL,
                PermissionScope.ORGANIZATION,
            }
        ),
        title="Приглашение в организацию",
    ),
)

DELETE_INVITATION = register_permission(
    Permission(
        resource="organization-invitations",
        action="delete",
        scopes=frozenset(
            {
                PermissionScope.GLOBAL,
                PermissionScope.ORGANIZATION,
            }
        ),
        title="Удаление приглашения в организацию",
    ),
)
