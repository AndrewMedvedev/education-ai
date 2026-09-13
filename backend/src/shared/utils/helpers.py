from collections.abc import AsyncIterable

from ..application.dtos import Pagination
from ..domain.entities import Entity
from ..domain.repos import Repository


async def iterate_batches[EntityT: Entity](
    repository: Repository[EntityT], start_page: int = 1, size: int = 50, **kwargs
) -> AsyncIterable[list[EntityT]]:
    """
    Итератор по коллекции сущностей (реализация паттерна batching)
    """

    page = start_page
    batch = await repository.paginate(Pagination(page=page, size=size), **kwargs)

    yield batch.items

    while batch.has_next:
        page += 1
        batch = await repository.paginate(Pagination(page=page, size=size), **kwargs)
        yield batch.items
