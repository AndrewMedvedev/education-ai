from typing import Protocol, Self, runtime_checkable

from collections.abc import Awaitable, Callable
from uuid import UUID

from src.activity.recorder import ActivityRecorder

from ..application.dtos import Page, Pagination
from .entities import Entity
from .events import EventPublisher
from .exceptions import NotFoundError


@runtime_checkable
class UnitOfWork(Protocol):
    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def flush(self) -> None: ...


class Repository[EntityT: Entity](Protocol):
    async def create(self, entity: EntityT) -> EntityT: ...

    async def read(self, uid: UUID) -> EntityT | None: ...

    async def paginate[T](
        self, pagination: Pagination, filters: T | None = None
    ) -> Page[EntityT]: ...

    async def update(self, entity: EntityT) -> None: ...

    async def delete(self, uid: UUID) -> None: ...

    async def exists(self, uid: UUID) -> bool: ...

    async def get_by_ids(self, ids: list[UUID]) -> list[EntityT]: ...


async def get_or_raise_404[EntityT: Entity](
    loader: Callable[[UUID], Awaitable[EntityT | None]],
    uid: UUID,
    aggregate_type: type[EntityT],
) -> EntityT:
    obj = await loader(uid)
    if obj is None:
        raise NotFoundError(f"{aggregate_type.__class__.__name__} with ID {uid} not found")

    return obj


async def finalize[EntityT: Entity](
    uow: UnitOfWork,
    *aggregates: EntityT,
    event_publisher: EventPublisher,
    activity_recorder: ActivityRecorder | None = None,
) -> None:
    events = []
    for aggregate in aggregates:
        events.extend(aggregate.collect_events())

    if activity_recorder is not None:
        await activity_recorder.record_all(events)

    await uow.commit()

    await event_publisher.publish_all(events)


class RepositoryDecorator[EntityT: Entity](Repository[EntityT]):
    def __init__(self, repo: Repository[EntityT]) -> None:
        self._repo = repo

    async def create(self, entity: EntityT) -> EntityT:
        return await self._repo.create(entity)

    async def read(self, uid: UUID) -> EntityT | None:
        return await self._repo.read(uid)

    async def paginate(self, pagination: Pagination) -> Page[EntityT]:
        return await self._repo.paginate(pagination)

    async def update(self, entity: EntityT) -> None:
        await self._repo.update(entity)

    async def delete(self, uid: UUID) -> None:
        await self._repo.delete(uid)

    async def exists(self, uid: UUID) -> bool:
        return await self._repo.exists(uid)

    async def get_by_ids(self, ids: list[UUID]) -> list[EntityT]:
        return await self._repo.get_by_ids(ids)
