from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.schemas import Page, Pagination

from ..domain.dtos import ActivityLogFilters
from ..domain.models import ActivityLog
from .models import ActivityLogOrm


class ActivityLogMapper:
    @staticmethod
    def to_orm(activity: ActivityLog) -> ActivityLogOrm:
        return ActivityLogOrm(
            aggregate_type=activity.aggregate_type,
            aggregate_id=activity.aggregate_id,
            action=activity.action,
            actor_id=activity.actor_id,
            occurred_on=activity.occurred_on,
            changes=activity.changes,
            meta=activity.meta,
            event_id=activity.event_id,
            correlation_id=activity.correlation_id,
        )

    @staticmethod
    def from_orm(orm: ActivityLogOrm) -> ActivityLog:
        return ActivityLog(
            aggregate_type=orm.aggregate_type,
            aggregate_id=orm.aggregate_id,
            action=orm.action,
            actor_id=orm.actor_id,
            occurred_on=orm.occurred_on,
            changes=orm.changes,
            meta=orm.meta,
            event_id=orm.event_id,
            correlation_id=orm.correlation_id,
        )


class SqlActivityLogRepository:
    model = ActivityLogOrm
    model_mapper = ActivityLogMapper

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_one(self, activity: ActivityLog) -> None:
        model = self.model_mapper.to_orm(activity)
        self.session.add(model)

    async def create_many(self, activities: list[ActivityLog]) -> None:
        models = [self.model_mapper.to_orm(activity) for activity in activities]
        self.session.add_all(models)

    def _apply_activity_log_filters(
            self, stmt: Select[tuple[ActivityLogOrm]], filters: ActivityLogFilters,
    ) -> Select[tuple[ActivityLogOrm]]:
        if filters.actor_id:
            stmt = stmt.where(self.model.actor_id == filters.actor_id)

        if filters.actions is not None and filters.actions:
            stmt = stmt.where(self.model.action.in_(filters.actions))

        if filters.occurred_after:
            stmt = stmt.where(self.model.occurred_on >= filters.occurred_after)

        if filters.occurred_before:
            stmt = stmt.where(self.model.occurred_on <= filters.occurred_before)

        return stmt

    async def get_for_aggregate(
            self,
            aggregate_type: str,
            aggregate_id: UUID,
            *,
            pagination: Pagination,
            filters: ActivityLogFilters | None = None,
    ) -> Page[ActivityLog]:
        stmt = select(self.model).where(
            (self.model.aggregate_type == aggregate_type) &
            (self.model.aggregate_id == aggregate_id)
        )

        if filters:
            stmt = self._apply_activity_log_filters(stmt, filters)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_items = await self.session.scalar(count_stmt) or 0

        if total_items == 0:
            return Page.create(
                items=[],
                total_items=total_items,
                page=pagination.page,
                size=pagination.size
            )

        stmt = (
            stmt
            .order_by(self.model.occurred_on.desc())
            .offset(pagination.offset)
            .limit(pagination.size)
        )
        results = await self.session.execute(stmt)
        models = results.scalars().all()

        return Page.create(
            items=[self.model_mapper.from_orm(model) for model in models],
            total_items=total_items,
            page=pagination.page,
            size=pagination.size
        )
