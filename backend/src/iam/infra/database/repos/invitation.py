from sqlalchemy import select

from src.iam.domain.entities import Invitation
from src.iam.domain.vo import Email
from src.iam.infra.database.mappers import InvitationMapper
from src.iam.infra.database.models import InvitationOrm
from src.shared.infra.database import SqlAlchemyRepository


class SqlInvitationRepository(SqlAlchemyRepository[Invitation, InvitationOrm]):
    model = InvitationOrm
    model_mapper = InvitationMapper

    async def get_by_token(self, token: str) -> Invitation | None:
        stmt = select(self.model).where(
            (self.model.token == token) & (self.model.deleted_at.is_(None)),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self.model_mapper.from_model(model) if model else None

    async def get_active_by_email(self, email: Email) -> tuple[Invitation, ...]:
        stmt = select(self.model).where(
            (self.model.email == email.value) & (self.model.deleted_at.is_(None)),
        )
        results = await self._session.execute(stmt)
        models = results.scalars().all()
        return tuple(self.model_mapper.from_model(model) for model in models)
