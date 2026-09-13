import abc
from collections.abc import Callable
from uuid import UUID

from sqlalchemy import Select, delete, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import Base

from ..application.dtos import Page, Pagination, TimeRangeFilters
from ..domain.entities import Entity


class ModelMapper[EntityT: Entity, ModelT: Base](abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def to_entity(model: ModelT) -> EntityT:
        """Преобразование ORM модели в доменную сущность"""

    @staticmethod
    @abc.abstractmethod
    def from_entity(entity: EntityT) -> ModelT:
        """Преобразование доменной сущности в ORM модель"""


class SqlAlchemyRepository[EntityT: Entity, ModelT: Base]:
    model: type[ModelT]
    model_mapper: ModelMapper[EntityT, ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, entity: EntityT) -> EntityT:

        model = self.model_mapper.from_entity(entity)
        self.session.add(model)
        return self.model_mapper.to_entity(model)

    async def read(self, uid: UUID) -> EntityT | None:
        stmt = select(self.model).where(self.model.id == uid)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def paginate(self, pagination: Pagination) -> Page[EntityT]:
        stmt = select(self.model).order_by(self.model.created_at.desc())
        return await self._paginate(stmt, pagination)

    async def _paginate(
        self,
        stmt: Select[tuple[ModelT]],
        pagination: Pagination,
        *,
        model_mapper: Callable[[ModelT], EntityT] | None = None,
    ) -> Page[EntityT]:
        if model_mapper is None:
            model_mapper = self.model_mapper.to_entity

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_items = await self.session.scalar(count_stmt)
        if total_items == 0:
            return Page.create([], total_items, pagination.page, pagination.size)

        stmt = (
            stmt
            .order_by(self.model.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.size)
        )
        results = await self.session.execute(stmt)
        models = results.scalars().all()

        return Page.create(
            items=[model_mapper(model) for model in models],
            total_items=total_items,
            page=pagination.page,
            size=pagination.size,
        )

    async def update(self, entity: EntityT) -> None:
        model = self.model_mapper.from_entity(entity)
        await self.session.merge(model)

    async def delete(self, uid: UUID) -> None:
        stmt = delete(self.model).where(self.model.id == uid)
        await self.session.execute(stmt)

    async def exists(self, uid: UUID) -> bool:
        stmt = select(exists()).where(self.model.id == uid)
        return await self.session.scalar(stmt)

    async def get_by_ids(self, ids: list[UUID]) -> list[EntityT]:
        stmt = select(self.model).where(self.model.id.in_(ids))
        results = await self.session.execute(stmt)
        return [self.model_mapper.to_entity(model) for model in results.scalars().all()]

    def _apply_time_range_filters(
        self,
        stmt: Select[tuple[ModelT]],
        filters: TimeRangeFilters,
    ) -> Select[tuple[ModelT]]:
        if filters.created_after:
            stmt = stmt.where(self.model.created_at >= filters.created_after)

        if filters.created_before:
            stmt = stmt.where(self.model.created_at <= filters.created_before)

        return stmt


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
            total_items=len(items),
            total_pages=1,
            has_next=False,
            has_prev=False,
            items=items[: params.size],
        )

    async def update(self, entity: EntityT) -> None:
        self.data[entity.id] = entity

    async def delete(self, uid: UUID) -> None:
        self.data.pop(uid)

    async def exists(self, uid: UUID) -> bool:
        return uid in self.data

    async def get_by_ids(self, ids: list[UUID]) -> list[EntityT]:
        return [entity for entity in self.data.values() if entity.id in ids]
