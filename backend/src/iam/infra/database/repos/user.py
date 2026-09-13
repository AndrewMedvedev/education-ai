from sqlalchemy import select

from src.iam.domain.entities import User
from src.iam.domain.vo import Email
from src.iam.infra.database.mappers import UserMapper
from src.iam.infra.database.models import UserOrm
from src.shared.infra.database import SqlAlchemyRepository


class SqlUserRepository(SqlAlchemyRepository[User, UserOrm]):
    model = UserOrm
    model_mapper = UserMapper

    async def get_by_email(self, email: Email) -> User | None:
        stmt = select(self.model).where(
            (self.model.email == email.value) & (self.model.deleted_at.is_(None)),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self.model_mapper.from_model(model) if model else None
