"""
Политики авторизации IAM BC.

Модуль policies отвечает за проверку доступа субъекта к конкретным
объектам и является вторым уровнем авторизации
после проверки permission (зависимость `require_permissions`).

Архитектура авторизации разделяет две независимые проверки:

1. Permission

   Отвечает на вопрос:
       «Имеет ли субъект право выполнять это действие вообще?»

   Например:
       'ticket.update'

   Наличие permission хранится в Identity и формируется при выпуске
   access token на основании ролей и назначенных им permissions.

2. Policy

   Отвечает на вопрос:
       «Может ли субъект применить это право к конкретному объекту?»

   Например, пользователь может иметь:
       'ticket.update'

   Но изменять только:
   - свои заявки;
   - заявки своей организации;
   - объекты, удовлетворяющие дополнительным условиям.

Policy тем самым реализует object-level authorization и позволяет отделить
общую IAM-модель от доменной модели конкретного bounded context.

### PermissionScope

Каждый Permission определяет набор допустимых scopes:

    Permission(
        resource="tickets",
        action="update",
        scopes=frozenset({PermissionScope.OWN, PermissionScope.ORGANIZATION})
    )

Scope описывает возможный способ применения permission, а не конкретное
разрешение пользователя.

Например:
    tickets.update
        ├── own
        └── organization

Это означает, что permission допускает как проверку собственных объектов,
так и объектов организации.

Scope не хранится в JWT и не входит в Identity. JWT содержит только
фактические permissions субъекта:
    {
        "perms": [
            "tickets.update",
        ]
    }

Scope определяется сервером во время применения permission к конкретному
ресурсу.

### Policy Registry

Конкретные object-level policies регистрируются в том bounded context,
которому принадлежит соответствующий ресурс.

IAM не должен знать структуру Ticket, User, Project, Workflow и других доменный объектов.

Например, Tickets BC может зарегистрировать:

    @register_policy(permissions.UPDATE, PermissionScope.OWN)
    def can_update_own_ticket(identity: Identity, ticket: Ticket) -> bool:
        return ticket.author_id == identity.id

    @register_policy(permissions.UPDATE, PermissionScope.ORGANIZATION)
    def can_update_organization_ticket(identity: Identity, ticket: Ticket) -> bool:
        return ticket.organization_id == identity.organization_id

Обе политики относятся к одному permission, но описывают разные способы
его применения.

При object-level проверке достаточно прохождения хотя бы одной
подходящей зарегистрированной policy.

### Проверка доступа

Для простой проверки возможности действия используется:

    has_permission(identity, permissions.UPDATE)

Для проверки доступа к конкретному ресурсу:

    can(identity, permissions.UPDATE, ticket)

Если необходима проверка с исключением:

    authorize(identity, permissions.UPDATE, ticket)

Семантика:

    has_permission()
        └── только permission

    can()
        └── permission + object-level policies

    authorize()
        └── can() + PermissionDeniedError

### Почему используется registry

Registry выбран вместо большого условного блока внутри IAM:

    if isinstance(resource, Ticket):
        ...
    elif isinstance(resource, User):
        ...
    elif isinstance(resource, Project):
        ...

Такой подход позволил бы IAM напрямую зависеть от всех bounded contexts
системы и нарушил бы их границы.

Вместо этого:

    IAM
      │
      ├── Permission
      ├── PermissionScope
      └── Policy Registry
               ▲
               │
        ┌──────┼────────┐
        │      │        │
      CRM   Tickets   Workflows

Каждый bounded context владеет собственными policies и определяет, как
его доменные объекты должны проверяться.

### Fail closed

Если permission отсутствует, доступ запрещается.

Если ресурс передан, но для permission не зарегистрировано ни одной
object-level policy, доступ также запрещается.

Таким образом, отсутствие policy не приводит к случайному предоставлению
доступа.

### Пример полного flow

Запрос:

    PATCH /tickets/{ticket_id}

1. HTTP authentication создаёт CurrentIdentity.
2. FastAPI dependency проверяет наличие:

       tickets.update

3. Application service загружает Ticket.
4. Application service вызывает:

       authorize(identity, permissions.UPDATE, ticket)

5. Authorization layer:
       - проверяет permission;
       - получает зарегистрированные policies;
       - применяет их к Ticket;
       - разрешает действие, если хотя бы одна policy возвращает True.
6. Только после успешной авторизации выполняется изменение Ticket.

Таким образом, endpoint-level permission и object-level authorization
остаются отдельными уровнями и могут переиспользоваться во всех модулях
системы.

### Архитектурная граница

IAM предоставляет универсальный механизм:

    Permission
    PermissionScope
    register_policy()
    has_permission()
    can()
    authorize()

Конкретные bounded contexts предоставляют только свои правила доступа:

    Tickets -> Ticket policies
    CRM -> CRM policies
    Workflows -> Workflow policies

Это позволяет в будущем заменить или расширить механизм object-level
authorization, не меняя Identity, JWT и базовые permission checks.
"""

from .authorization import authorize, can, has_permission
from .registry import get_permission_policies, register_policy

__all__ = [
    "authorize",
    "can",
    "get_permission_policies",
    "has_permission",
    "register_policy",
]
