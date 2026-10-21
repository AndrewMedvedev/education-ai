from uuid import UUID

from sqlalchemy import select

from src.shared.application.dtos import Page, Pagination
from src.shared.infra.database.repos.sqlalchemy import SqlAlchemyRepository, paginate

from ....application.dtos import FeedbackFilters
from ....domain.entities import Feedback
from ..mappers import FeedbackMapper
from ..models import FeedbackOrm


class SqlFeedbackRepository(SqlAlchemyRepository[Feedback, FeedbackOrm]):
    model = FeedbackOrm
    model_mapper = FeedbackMapper  # pyright: ignore[reportAssignmentType]

    async def find(
        self,
        pagination: Pagination,
        filters: FeedbackFilters | None = None,
        *,
        user_id: UUID | None = None,
    ) -> Page[Feedback]:
        """Возвращает отзывы с применением фильтров."""

        stmt = select(self.model).where(self.model.deleted_at.is_(None))

        if user_id is not None:
            stmt = stmt.where(self.model.user_id == user_id)

        if filters:
            if filters.rating is not None:
                stmt = stmt.where(self.model.rating == filters.rating)

            if filters.created_after is not None:
                stmt = stmt.where(self.model.created_at >= filters.created_after)

            if filters.created_before is not None:
                stmt = stmt.where(self.model.created_at <= filters.created_before)

        sort = filters.sort if filters and filters.sort else "created_at:desc"

        return await paginate(
            session=self._session,
            model=self.model,
            stmt=stmt,
            pagination=pagination,
            mapper=self.model_mapper.from_model,
            sort=sort,
        )
