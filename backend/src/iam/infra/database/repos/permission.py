from typing import ClassVar

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.iam.application.dtos import PermissionQueryParamFilters
from src.iam.domain.entities import Permission
from src.iam.infra.database.mappers import PermissionMapper
from src.iam.infra.database.models import PermissionOrm
from src.shared.application.dtos import Page, Pagination
from src.shared.infra.database.repos.sqlalchemy import paginate


def apply_permission_query_param_filters(
    stmt: Select[tuple[PermissionOrm]],
    model: type[PermissionOrm],
    filters: PermissionQueryParamFilters,
) -> Select[tuple[PermissionOrm]]:

    def _filter_resource(value: str): return model.resource == value
    def _filter_action(value: str): return model.action == value
    def _filter_scopes(value: list[str]): return model.scopes.op("?|")(value) if value else None

    filters_map = {
        "resource": _filter_resource,
        "action": _filter_action,
        "scopes": _filter_scopes,
    }

    conditions = [
        condition
        for field, value in filters.model_dump(exclude_none=True).items()
        if field in filters_map and (condition := filters_map[field](value)) is not None
    ]

    if not conditions:
        return stmt

    op = and_ if filters.op == "and" else or_
    return stmt.where(op(*conditions))


class SqlPermissionRepository:
    model: ClassVar[type[PermissionOrm]] = PermissionOrm
    model_mapper: ClassVar[type[PermissionMapper]] = PermissionMapper

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_or_update(self, permission: Permission) -> None:
        values = self.model_mapper.to_dict(permission)

        insert_stmt = pg_insert(self.model).values(**values)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            constraint="uq_resource_action",
            set_={
                "title": insert_stmt.excluded.title,
                "description": insert_stmt.excluded.description,
                "scopes": insert_stmt.excluded.scopes,
            },
        )
        await self._session.execute(upsert_stmt)

    async def find(
            self, pagination: Pagination, filters: PermissionQueryParamFilters | None = None,
    ) -> Page[Permission]:

        stmt = select(self.model)

        if filters:
            stmt = apply_permission_query_param_filters(stmt, self.model, filters)

        return await paginate(
            session=self._session,
            model=self.model,
            stmt=stmt,
            pagination=pagination,
            mapper=self.model_mapper.from_model,
            sort=filters.sort,
        )
