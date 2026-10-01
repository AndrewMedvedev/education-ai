from src.iam.domain.entities import Permission
from src.iam.domain.vo import PermissionScope

from .registry import register_permission

CREATE = register_permission(
    Permission(
        resource="memberships",
        action="create",
        scopes=frozenset(
            {
                PermissionScope.GLOBAL,
                PermissionScope.ORGANIZATION,
            }
        ),
        title="Создание членства",
    ),
)

READ = register_permission(
    Permission(
        resource="memberships",
        action="read",
        scopes=frozenset(
            {
                PermissionScope.GLOBAL,
                PermissionScope.ORGANIZATION,
                PermissionScope.COURSE,
            }
        ),
        title="Просмотр членства",
    ),
)
