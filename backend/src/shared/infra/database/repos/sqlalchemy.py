from typing import Any

from collections.abc import Callable
from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    Select,
    UnaryExpression,
    asc,
    delete,
    desc,
    exists,
    func,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import Base
from src.shared.application.dtos import BaseQueryParamFilters, Page, Pagination
from src.shared.domain.entities import Entity
from src.shared.infra.database.mappers import ModelMapper


def _parse_sort_param(
    sort: str,
) -> tuple[str, Callable[[ColumnElement[Any]], UnaryExpression[Any]]]:
    """
    Парсит строку сортировки и возвращает кортеж (имя_поля, функция_сортировки).
    Поддерживает форматы "field:asc"/"field:desc" и "-field"/"field".
    """

    if ":" in sort:
        field_name, direction = sort.split(":", maxsplit=1)
        sort_func = asc if direction.lower() == "asc" else desc

        return field_name, sort_func

    if sort.startswith("-"):
        field_name, sort_func = sort[1:], desc
    else:
        field_name, sort_func = sort, asc

    return field_name, sort_func


def apply_sorting[ModelT: Base](
    stmt: Select[tuple[ModelT]],
    model: type[ModelT],
    sort: str | None = None,
) -> Select[tuple[ModelT]]:
    """Динамически накладывает order_by на основе параметров из фильтра."""

    default_stmt = stmt.order_by(model.created_at)

    if sort is None:
        return default_stmt

    try:
        field_name, sort_func = _parse_sort_param(sort)

        if (column := getattr(model, field_name, None)) is not None:
            return stmt.order_by(sort_func(column))

    except (AttributeError, ValueError):
        raise ValueError(f"Invalid sort query param - '{sort}'") from None

    return default_stmt


async def paginate[ModelT: Base, ItemT](
    session: AsyncSession,
    model: type[ModelT],
    stmt: Select[tuple[ModelT]],
    pagination: Pagination,
    *,
    mapper: Callable[[ModelT], ItemT] | None = None,
    sort: str | None = "created_at:desc",
) -> Page[ItemT]:
    count_stmt = select(func.count()).select_from(stmt.subquery())

    if not (total := await session.scalar(count_stmt)):
        return Page.create([], total, pagination.page, pagination.size)

    stmt = stmt.offset(pagination.offset).limit(pagination.size)
    stmt = apply_sorting(stmt, model, sort=sort)

    results = await session.execute(stmt)
    models = results.scalars().all()

    items = [mapper(model) for model in models] if mapper else models

    return Page.create(
        items=items,
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


class SqlAlchemyRepository[EntityT: Entity, ModelT: Base]:
    model: type[ModelT]
    model_mapper: ModelMapper[EntityT, ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, entity: EntityT) -> EntityT:

        model = self.model_mapper.to_model(entity)
        self._session.add(model)
        return self.model_mapper.from_model(model)

    async def read(self, uid: UUID) -> EntityT | None:
        stmt = select(self.model).where(self.model.id == uid)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.from_model(model)

    async def find[FiltersT: BaseQueryParamFilters](
        self,
        pagination: Pagination,
        filters: FiltersT | None = None,
    ) -> Page[EntityT]:
        """Для расширения логики фильтрации можно переопределить в дочерних классах."""

        stmt = select(self.model)

        return await paginate(
            session=self._session,
            model=self.model,
            stmt=stmt,
            pagination=pagination,
            mapper=self.model_mapper.from_model,
            sort=filters.sort if filters else None,
        )

    async def update(self, uid: UUID, **kwargs) -> EntityT | None:
        stmt = (
            update(self.model).values(**kwargs).where(self.model.id == uid).returning(self.model)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.from_model(model)

    async def upsert(self, entity: EntityT) -> None:
        model = self.model_mapper.to_model(entity)
        await self._session.merge(model)

    async def delete(self, uid: UUID) -> None:
        stmt = delete(self.model).where(self.model.id == uid)
        await self._session.execute(stmt)

    async def exists(self, uid: UUID) -> bool | None:
        stmt = select(exists().where(self.model.id == uid))
        return await self._session.scalar(stmt)

    async def get_by_ids(self, ids: list[UUID]) -> list[EntityT]:
        stmt = select(self.model).where(self.model.id.in_(ids))
        results = await self._session.execute(stmt)
        return [self.model_mapper.from_model(model) for model in results.scalars().all()]
