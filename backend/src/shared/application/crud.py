from typing import Any

from collections.abc import Awaitable, Callable
from uuid import UUID

from pydantic import BaseModel

from src.shared.domain.entities import Entity
from src.shared.domain.exceptions import UnsupportedOperationError

from .dtos import Page, Pagination
from .repos import Repository, get_or_raise_404
from .transaction import Transaction


async def _method_not_allowed_stub(*args: Any, **kwargs: Any) -> Any:  # noqa: RUF029, ARG001
    raise UnsupportedOperationError("This CRUD method not allowed.")


class Crud[
    EntityT: Entity,
    ResponseT: BaseModel,
    **CreateP,
    **UpdateP,
    **DeleteP,
]:
    def __init__(
            self,
            repository: Repository[EntityT],
            transaction: Transaction,
            to_response: Callable[[EntityT], ResponseT],
            *,
            create_handler: Callable[CreateP, Awaitable[EntityT]] = _method_not_allowed_stub,
            update_handler: Callable[UpdateP, Awaitable[EntityT]] = _method_not_allowed_stub,
            delete_handler: Callable[DeleteP, Awaitable[EntityT]] = _method_not_allowed_stub,
    ) -> None:
        self._repository = repository
        self._transaction = transaction
        self._to_response = to_response

        self._create_handler = create_handler
        self._update_handler = update_handler
        self._delete_handler = delete_handler

    async def create(self, *args: CreateP.args, **kwargs: CreateP.kwargs) -> ResponseT:

        if self._create_handler is None:
            ...

        entity = await self._create_handler(*args, **kwargs)

        await self._repository.create(entity)
        await self._transaction(entity)

        return self._to_response(entity)

    async def read(self, uid: UUID) -> ResponseT:
        entity = await get_or_raise_404(self._repository.read, uid, type[EntityT])
        return self._to_response(entity)

    async def paginate[FilterT](
            self, pagination: Pagination, filters: FilterT | None = None,
    ) -> Page[ResponseT]:
        page = await self._repository.find(pagination, filters)
        return page.to_response(self._to_response)

    async def update(self, *args: UpdateP.args, **kwargs: UpdateP.kwargs) -> ResponseT:

        entity = await self._update_handler(*args, **kwargs)

        await self._repository.update(entity)
        await self._transaction(entity)

        return self._to_response(entity)

    async def delete(self, *args: DeleteP.args, **kwargs: DeleteP.kwargs) -> None:

        entity = await self._delete_handler(*args, **kwargs)

        await self._repository.update(entity)  # Soft-delete
        await self._transaction(entity)
