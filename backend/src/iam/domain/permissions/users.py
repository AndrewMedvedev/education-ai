from src.iam.domain.entities import Permission
from src.iam.domain.vo import PermissionScope

from .registry import register_permission

READ = register_permission(
    Permission(
        resource="users",
        action="read",
        scopes=frozenset({PermissionScope.ORGANIZATION, PermissionScope.OWN}),
        title="Просмотр пользователей",
    ),
)

UPDATE = register_permission(
    Permission(
        resource="users",
        action="update",
        scopes=frozenset({PermissionScope.ORGANIZATION, PermissionScope.OWN}),
        title="Изменение пользователей",
    ),
)

DEACTIVATE = register_permission(
    Permission(
        resource="users",
        action="deactivate",
        scopes=frozenset({PermissionScope.ORGANIZATION}),
        title="Деактивация пользователя",
    ),
)
