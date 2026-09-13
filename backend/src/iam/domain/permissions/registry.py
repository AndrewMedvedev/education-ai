"""
Реестр системных разрешений IAM.

Permission Registry является источником истины для всех доступных
разрешений в системе.

Разрешения объявляются в коде при старте приложения и используются
в проверках авторизации, настройке ролей и построении политик доступа.

Пример объявления разрешения:

```python
from src.iam.permissions import register_permission
from src.iam.domain.entities import Permission
from src.iam.domain.scopes import PermissionScope

register_permission(
    Permission(
        resource="tickets",
        action="create",
        scope=PermissionScope.ORGANIZATION,
        description="Создание заявок",
    )
)
```


Роли при этом хранят только ссылки на коды разрешений:

{
    "tickets.create",
    "tickets.read",
}

Registry намеренно не хранит разрешения в базе данных.

Причины:

- разрешения являются частью бизнес-контракта приложения;
- код, выполняющий проверку доступа, всё равно зависит от конкретного
  permission code;
- добавление нового разрешения требует изменения приложения, а не
  пользовательской настройки;
- база данных хранит только пользовательскую конфигурацию:
  роли, назначение ролей и набор доступных прав.

Если требуется динамическая настройка прав без изменения приложения,
следует использовать отдельный механизм feature permissions или ACL,
а не изменять системный registry.

Registry должен инициализироваться при импорте модулей с permission
definitions до первого использования авторизации.
"""

from src.iam.domain.entities import Permission

_permission_registry: dict[str, Permission] = {}


def register_permission(permission: Permission) -> Permission:
    """Зарегистрировать системное разрешение."""

    if permission.code in _permission_registry:
        raise ValueError(f"Permission already registered: {permission.code}.")

    _permission_registry[permission.code] = permission
    return permission


def get_permissions() -> tuple[Permission, ...]:
    """Получить список всех зарегистрированных системой разрешений."""

    return tuple(_permission_registry.values())
