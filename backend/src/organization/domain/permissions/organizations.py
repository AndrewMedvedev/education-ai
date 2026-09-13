from src.iam.domain.entities import Permission
from src.iam.domain.permissions.registry import register_permission
from src.iam.domain.vo import PermissionScope

CREATE = register_permission(
    Permission(
        resource="organization",
        action="create",
        scopes=frozenset({PermissionScope.GLOBAL}),
        title="Создание организации",
        description=(
            "Разрешает создать новую организацию, указав её наименование, адрес "
            "электронной почты и описание. Право доступно только в глобальном scope "
            "и предназначено для администраторов платформы. Организацию нельзя "
            "создать с адресом электронной почты, который уже используется другой "
            "организацией."
        ),
    ),
)

READ = register_permission(
    Permission(
        resource="organization",
        action="read",
        scopes=frozenset({PermissionScope.GLOBAL}),
        title="Просмотр списка организаций",
        description=(
            "Разрешает получить постраничный список организаций платформы. Право "
            "доступно только в глобальном scope и предназначено для пользователей, "
            "которым необходим обзор всех организаций, а не доступ к одной конкретной "
            "организации."
        ),
    ),
)

ORGANIZATION_READ = register_permission(
    Permission(
        resource="organization",
        action="organization_read",
        scopes=frozenset({PermissionScope.ORGANIZATION, PermissionScope.OWN}),
        title="Просмотр организации",
        description=(
            "Разрешает просматривать подробную информацию об отдельной организации "
            "по её идентификатору. Scope organization ограничивает доступ текущей "
            "организацией пользователя, а scope own — собственной организацией "
            "пользователя; право не предоставляет доступ к общему списку организаций."
        ),
    ),
)


UPDATE = register_permission(
    Permission(
        resource="organization",
        action="update",
        scopes=frozenset({
            PermissionScope.ORGANIZATION,
            PermissionScope.OWN,
            PermissionScope.GLOBAL,
        }),
        title="Изменение организации",
        description=(
            "Разрешает частично изменять данные организации: наименование, адрес "
            "электронной почты и описание. Scope global позволяет изменять любую "
            "организацию платформы, scope organization ограничивает действие текущей "
            "организацией пользователя, а scope own — собственной организацией "
            "пользователя. Неуказанные поля остаются без изменений."
        ),
    ),
)

DELETE = register_permission(
    Permission(
        resource="organization",
        action="delete",
        scopes=frozenset({
            PermissionScope.GLOBAL,
        }),
        title="Удаление организации",
        description=(
            "Разрешает деактивировать любую организацию платформы. Операция выполняет "
            "мягкое удаление: организация сохраняется в базе данных, но помечается как "
            "неактивная. Право доступно только в глобальном scope и предназначено для "
            "администраторов платформы."
        ),
    ),
)
