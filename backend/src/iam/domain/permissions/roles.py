from src.iam.domain.entities import Permission
from src.iam.domain.vo import PermissionScope

from .registry import register_permission

CREATE = register_permission(
    Permission(
        resource="roles",
        action="create",
        scopes=frozenset({PermissionScope.GLOBAL, PermissionScope.ORGANIZATION}),
        title="Создание ролей",
    ),
)

READ = register_permission(
    Permission(
        resource="roles",
        action="read",
        scopes=frozenset({PermissionScope.GLOBAL, PermissionScope.ORGANIZATION}),
        title="Просмотр ролей",
    ),
)

UPDATE = register_permission(
    Permission(
        resource="roles",
        action="update",
        scopes=frozenset({PermissionScope.GLOBAL, PermissionScope.ORGANIZATION}),
        title="Изменение ролей",
    ),
)

DELETE = register_permission(
    Permission(
        resource="roles",
        action="delete",
        scopes=frozenset({PermissionScope.GLOBAL, PermissionScope.ORGANIZATION}),
        title="Удаление ролей",
    ),
)
