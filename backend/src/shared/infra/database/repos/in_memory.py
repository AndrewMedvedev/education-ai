from uuid import UUID

from src.shared.application.dtos import Page, Pagination
from src.shared.domain.entities import Entity


class InMemoryRepository[EntityT: Entity]:
    def __init__(self) -> None:
        self.data = {}

    async def create(self, entity: EntityT) -> EntityT:
        self.data[entity.id] = entity
        return entity

    async def read(self, uid: UUID) -> EntityT | None:
        return self.data.get(uid)

    async def paginate(self, params: Pagination) -> Page[EntityT]:
        items = list(self.data.values())
        return Page(
            page=params.page,
            size=params.size,
            total=len(items),
            pages=1,
            has_next=False,
            has_prev=False,
            items=items[:params.size],
        )

    async def update(self, entity: EntityT) -> None:
        self.data[entity.id] = entity

    async def delete(self, uid: UUID) -> None:
        self.data.pop(uid)

    async def exists(self, uid: UUID) -> bool:
        return uid in self.data

    async def get_by_ids(self, ids: list[UUID]) -> list[EntityT]:
        return [entity for entity in self.data.values() if entity.id in ids]
