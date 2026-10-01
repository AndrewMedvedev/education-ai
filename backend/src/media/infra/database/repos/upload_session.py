from uuid import UUID

from sqlalchemy import select, update

from src.media.domain.entities import UploadSession
from src.shared.infra.database.repos.sqlalchemy import SqlAlchemyRepository

from ..mappers import UploadSessionMapper
from ..models import UploadSessionOrm


class SqlUploadSessionRepository(SqlAlchemyRepository[UploadSession, UploadSessionOrm]):
    model = UploadSessionOrm
    model_mapper = UploadSessionMapper  # pyright: ignore[reportAssignmentType]

    async def update(self, storage_key: str, **kwargs) -> UploadSession | None:
        stmt = (
            update(self.model)
            .values(**kwargs)
            .where(self.model.storage_key == storage_key)
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.from_model(model)

    async def get_by_storage_key(self, storage_key: str) -> UploadSession | None:
        """Получает by storage key, чтобы вызывающий код работал через единый интерфейс."""
        stmt = select(self.model).where(self.model.storage_key == storage_key)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.from_model(model)

    async def get_by_owner(self, uploaded_by: UUID) -> list[UploadSession]:
        """Получает by owner, чтобы вызывающий код работал через единый интерфейс."""
        stmt = select(self.model).where(self.model.uploaded_by == uploaded_by)
        results = await self._session.execute(stmt)
        models = results.scalars().all()
        return [self.model_mapper.from_model(model) for model in models]
