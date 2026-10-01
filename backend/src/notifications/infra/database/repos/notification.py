from uuid import UUID

from sqlalchemy import func, select

from src.shared.application.dtos import Page, Pagination
from src.shared.infra.repos import SqlAlchemyRepository

from ....domain.entities import Notification
from ..mappers import NotificationMapper
from ..models import NotificationOrm


class SqlNotificationRepository(SqlAlchemyRepository[Notification, NotificationOrm]):
    model = NotificationOrm
    model_mapper = NotificationMapper  # pyright: ignore[reportAssignmentType]

    async def get_unread_count(self, user_id: UUID) -> int | None:
        # Формирование запроса
        stmt = select(self.model).where(
            (self.model.user_id == user_id) & (self.model.read.is_(False))
        )
        count_stmt = select(func.count()).select_from(stmt.subquery())

        return await self.session.scalar(count_stmt)

    async def get_by_user(
        self,
        user_id: UUID,
        pagination: Pagination,
        unread_only: bool = False,
    ) -> Page[Notification]:
        stmt = select(self.model).where(self.model.user_id == user_id)

        if unread_only:
            stmt = stmt.where(self.model.read.is_(False))

        return await self._paginate(stmt, pagination)

    async def get_by_email(
        self,
        email: str,
        pagination: Pagination,
        unread_only: bool = False,
    ) -> Page[Notification]:
        stmt = select(self.model).where(self.model.email == email)

        if unread_only:
            stmt = stmt.where(self.model.read.is_(False))

        return await self._paginate(stmt, pagination)
