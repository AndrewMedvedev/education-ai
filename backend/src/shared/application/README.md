# CRUD - билдер

`Crud` - это шаблонный application service для реализации типовых CRUD-сценариев.

Его задача — убрать повторяющийся инфраструктурный код (repository, transaction, mapping) и оставить в сервисах только бизнес-логику.

Crud не заменяет Application Service и не содержит бизнес-логики. Вся бизнес-логика по-прежнему реализуется в обработчиках (create_handler, update_handler, delete_handler).

## Pipeline

Каждая операция выполняется по одному и тому же шаблону.

```text
         Input DTO
            │
            ▼
        handler(...) // кастомная логика
            │
            ▼
        Aggregate
            │
            ▼
     Repository.crud(...)
            │
            ▼
       Transaction(...)
(commit + activity + domain events)
            │
            ▼
        Response DTO
```

### Что относится к бизнес-логике

Обработчики (`*_handler`) содержат всю бизнес-логику use case.

Например:
 - загрузка агрегатов;
 - проверки существования;
 - авторизация;
 - дополнительные запросы в репозитории;
 - создание доменных объектов;
 - вызов доменных методов;
 - любые доменные проверки.

Именно обработчик решает, что должно произойти.


### Что делает Crud

После успешного выполнения обработчика Crud всегда выполняет одинаковые действия:

 1. сохраняет агрегат через Repository;
 2. завершает транзакцию (Transaction);
 3. публикует доменные события;
 4. записывает Activity Log (если нужно);
 5. преобразует агрегат в Response DTO.

Таким образом, Crud отвечает только за инфраструктурный pipeline.

## Практический пример

### create_handler
```python
from src.iam.domain.authz import Subject
from src.iam.domain.exceptions import PermissionDeniedError
from src.tickets.domain.entities import Ticket
from src.tickets.schemas import TicketCreate

async def create_ticket(
    data: TicketCreate,
    current_subject: Subject,
) -> Ticket:

    project = await ...

    permission = await ...

    if not permission.allowed:
        raise PermissionDeniedError(permission.reason)

    return Ticket.create(...)
```

### Конфигурация CRUD
```python
ticket_crud = Crud[
    Ticket,
    TicketResponse,
    [TicketCreate, Subject],
    [UUID, TicketUpdate, Subject],
    [UUID, Subject],
](
    repository=ticket_repository,
    transaction=transaction,
    to_response=map_ticket_to_response,

    create_handler=create_ticket,
    update_handler=edit_ticket,
    delete_handler=archive_ticket,
)
```

# Вызов метода
```python
response = await ticket_crud.create(request, current_subject)
```