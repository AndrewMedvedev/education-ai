from src.iam.domain.entities import Permission
from src.iam.domain.permissions.registry import register_permission
from src.iam.domain.vo import PermissionScope

CREATE = register_permission(
    Permission(
        resource="ai_model",
        action="create",
        scopes=frozenset({PermissionScope.GLOBAL}),
        title="Создание ии модели",
    ),
)


DELETE = register_permission(
    Permission(
        resource="ai_model",
        action="delete",
        scopes=frozenset({
            PermissionScope.GLOBAL,
        }),
        title="Удаление ии модели",
    ),
)
