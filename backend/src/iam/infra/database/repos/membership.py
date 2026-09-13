from uuid import UUID

from sqlalchemy import select

from src.iam.domain.entities import Membership
from src.iam.infra.database.mappers import MembershipMapper
from src.iam.infra.database.models import MembershipOrm
from src.shared.infra.database import SqlAlchemyRepository


class SqlMembershipRepository(SqlAlchemyRepository[Membership, MembershipOrm]):
    model = MembershipOrm
    model_mapper = MembershipMapper

    async def get_by_user(self, user_id: UUID) -> tuple[Membership, ...]:
        stmt = select(self.model).where(
            (self.model.user_id == user_id) & (self.model.deleted_at.is_(None)),
        )
        results = await self._session.execute(stmt)
        models = results.scalars().all()
        return tuple(self.model_mapper.from_model(model) for model in models)

    async def get_by_user_and_organization(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> Membership | None:
        stmt = select(self.model).where(
            (self.model.user_id == user_id) & (self.model.organization_id == organization_id),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self.model_mapper.from_model(model) if model else None
