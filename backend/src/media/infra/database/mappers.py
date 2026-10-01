from src.media.domain.entities import StoredObject, UploadSession
from src.shared.infra.database.mappers import ModelMapper

from .models import StoredObjectOrm, UploadSessionOrm


class UploadSessionMapper(ModelMapper):
    @staticmethod
    def from_model(model: UploadSessionOrm) -> UploadSession:
        """Преобразует данные в доменную сущность, чтобы передать их в нужный слой приложения."""
        return UploadSession(
            id=model.id,
            updated_at=model.updated_at,
            created_at=model.created_at,
            storage_key=model.storage_key,
            filename=model.filename,
            content_type=model.content_type,
            size_bytes=model.size_bytes,
            sha256=model.sha256,
            uploaded_by=model.uploaded_by,
            status=model.status,
            expires_at=model.expires_at,
            object_id=model.object_id,
        )

    @staticmethod
    def to_model(entity: UploadSession) -> UploadSessionOrm:
        """Преобразует доменную сущность в ORM модель, чтобы сохранить ее в базе данных."""
        return UploadSessionOrm(
            id=entity.id,
            updated_at=entity.updated_at,
            created_at=entity.created_at,
            storage_key=entity.storage_key,
            filename=entity.filename,
            content_type=entity.content_type,
            size_bytes=entity.size_bytes,
            sha256=entity.sha256,
            uploaded_by=entity.uploaded_by,
            status=entity.status,
            expires_at=entity.expires_at,
            object_id=entity.object_id,
        )


class StoredObjectMapper(ModelMapper):
    @staticmethod
    def from_model(model: StoredObjectOrm) -> StoredObject:
        """Преобразует данные в доменную сущность, чтобы передать их в нужный слой приложения."""
        return StoredObject(
            id=model.id,
            updated_at=model.updated_at,
            created_at=model.created_at,
            storage_key=model.storage_key,
            size_bytes=model.size_bytes,
            sha256=model.sha256,
            content_type=model.content_type,
        )

    @staticmethod
    def to_model(entity: StoredObject) -> StoredObjectOrm:
        """Преобразует доменную сущность в ORM модель, чтобы сохранить ее в базе данных."""
        return StoredObjectOrm(
            id=entity.id,
            updated_at=entity.updated_at,
            created_at=entity.created_at,
            storage_key=entity.storage_key,
            size_bytes=entity.size_bytes,
            sha256=entity.sha256,
            content_type=entity.content_type,
        )
