from uuid import UUID

from sqlalchemy import select

from src.shared.infra.database.mappers import ModelMapper
from src.shared.infra.database.repos.sqlalchemy import SqlAlchemyRepository

from ..domain.entities import Attachment
from .models import AttachmentOrm


class AttachmentMapper(ModelMapper):
    @staticmethod
    def from_model(model: AttachmentOrm) -> Attachment:
        """Преобразует данные в доменную сущность, чтобы передать их в нужный слой приложения."""
        return Attachment(
            id=model.id,
            updated_at=model.updated_at,
            created_at=model.created_at,
            original_filename=model.original_filename,
            mime_type=model.mime_type,
            size_bytes=model.size_bytes,
            storage_key=model.storage_key,
            owner_id=model.owner_id,
            uploaded_at=model.uploaded_at,
            uploaded_by=model.uploaded_by,
        )

    @staticmethod
    def to_model(entity: Attachment) -> AttachmentOrm:
        """Создаёт объект из доменную сущность, чтобы восстановить доменную модель из внешнего формата."""
        return AttachmentOrm(
            id=entity.id,
            updated_at=entity.updated_at,
            created_at=entity.created_at,
            original_filename=entity.original_filename,
            mime_type=entity.mime_type,
            size_bytes=entity.size_bytes,
            storage_key=entity.storage_key,
            owner_id=entity.owner_id,
            uploaded_at=entity.uploaded_at,
            uploaded_by=entity.uploaded_by,
        )


class SqlAttachmentRepository(SqlAlchemyRepository[Attachment, AttachmentOrm]):
    model = AttachmentOrm
    model_mapper = AttachmentMapper  # pyright: ignore[reportAssignmentType]

    async def get_by_storage_key(self, storage_key: str) -> Attachment | None:
        """Получает by storage key, чтобы вызывающий код работал через единый интерфейс."""
        stmt = select(self.model).where(self.model.storage_key == storage_key)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.from_model(model)

    async def get_by_owner(self, owner_id: UUID) -> list[Attachment]:
        """Получает by owner, чтобы вызывающий код работал через единый интерфейс."""
        stmt = select(self.model).where(self.model.owner_id == owner_id)
        results = await self._session.execute(stmt)
        models = results.scalars().all()
        return [self.model_mapper.from_model(model) for model in models]
