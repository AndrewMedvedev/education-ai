from src.iam.domain.entities import Permission
from src.iam.domain.permissions.registry import register_permission
from src.iam.domain.vo import PermissionScope

CREATE = register_permission(
    Permission(
        resource="course",
        action="create",
        scopes=frozenset({
            PermissionScope.ORGANIZATION,
            PermissionScope.OWN,
        }),
        title="Создание курса",
    ),
)

READ = register_permission(
    Permission(
        resource="course",
        action="read",
        scopes=frozenset(PermissionScope),
        title="Просмотр списка курсов",
    ),
)

COURSE_READ = register_permission(
    Permission(
        resource="course",
        action="course_read",
        scopes=frozenset({PermissionScope.COURSE}),
        title="Прохождение курса",
    ),
)


UPDATE = register_permission(
    Permission(
        resource="course",
        action="update",
        scopes=frozenset({
            PermissionScope.ORGANIZATION,
            PermissionScope.COURSE,
            PermissionScope.OWN,
        }),
        title="Изменение курса",
    ),
)

DELETE = register_permission(
    Permission(
        resource="course",
        action="delete",
        scopes=frozenset({
            PermissionScope.ORGANIZATION,
            PermissionScope.COURSE,
            PermissionScope.OWN,
        }),
        title="Удаление курса",
    ),
)
