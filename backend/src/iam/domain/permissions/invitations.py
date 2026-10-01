from src.iam.domain.entities import Permission
from src.iam.domain.vo import PermissionScope

from .registry import register_permission

INVITE = register_permission(
    Permission(
        resource="invitations",
        action="invite",
        scopes=frozenset(
            {
                PermissionScope.GLOBAL,
                PermissionScope.ORGANIZATION,
                PermissionScope.COURSE,
            }
        ),
        title="Приглашение в систему",
    ),
)

DELETE_INVITATION = register_permission(
    Permission(
        resource="invitations",
        action="delete",
        scopes=frozenset(
            {
                PermissionScope.GLOBAL,
                PermissionScope.ORGANIZATION,
                PermissionScope.COURSE,
            }
        ),
        title="Удаление приглашения",
    ),
)
