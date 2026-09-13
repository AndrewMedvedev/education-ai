from sqlalchemy import select

from src.iam.domain.entities import ServiceAccount
from src.iam.infra.database.mappers import ServiceAccountMapper
from src.iam.infra.database.models import ServiceAccountOrm
from src.shared.infra.database.repos import SqlAlchemyRepository


class SqlServiceAccountRepository(SqlAlchemyRepository[ServiceAccount, ServiceAccountOrm]):
    model = ServiceAccountOrm
    model_mapper = ServiceAccountMapper

    async def get_by_client_id(self, client_id: str) -> ServiceAccount | None:
        stmt = select(self.model).where(
            (self.model.client_id == client_id) & (self.model.deleted_at.is_(None)),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.from_model(model)
