from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.domain.exceptions import BadRequestError, ForbiddenError, NotFoundError

from ..domain.constants import PRESIGNED_URL_EXPIRES_IN
from ..domain.entities import StoredObject, UploadSession
from ..domain.vo import UploadStatus
from .dtos import (
    CreateUploadDTO,
    ObjectMeta,
    PresignedDownloadResponse,
    UploadInfo,
    UploadResponse,
)
from .repos import Storage, StoredObjectRepository, UploadSessionRepository


def validate_uploaded_object(upload: UploadSession, obj_meta: ObjectMeta) -> None:
    """Проверяет фактические данные с заявленными."""

    if upload.size_bytes != obj_meta.size:
        raise BadRequestError("The stated size does not match the actual size.")

    if upload.sha256 != obj_meta.checksum:
        raise BadRequestError("The declared hash does not match the actual hash.")


def validate_upload_ownership(upload: UploadSession, user_id: UUID | None) -> None:
    """Проверяет, является ли пользователь владельцем сессии загрузки."""
    if upload.uploaded_by is not None and upload.uploaded_by != user_id:
        raise ForbiddenError(
            "Insufficient permissions to access the upload db.",
        )


def is_valid_upload_status_to_complete(upload: UploadSession) -> bool:
    """Проверяет статус загрузочной сессии для её завершения."""

    if upload.status == UploadStatus.COMPLETED:
        return True

    if upload.status != UploadStatus.PENDING:
        raise BadRequestError(
            f"Cannot complete upload db. Invalid status: {upload.status}.",
        )

    return False


class AttachmentService:
    def __init__(
        self,
        session: AsyncSession,
        storage: Storage,
        upload_session_repo: UploadSessionRepository,
        stored_object_repo: StoredObjectRepository,
    ) -> None:
        """Инициализирует объект и сохраняет зависимости, необходимые для дальнейшей работы."""
        self.session = session
        self.storage = storage
        self.upload_session_repo = upload_session_repo
        self.stored_object_repo = stored_object_repo

    async def create_presigned_upload_url(
        self,
        request: CreateUploadDTO,
        uploaded_by: UUID,
    ) -> UploadResponse:
        """Создание подписанного URL для прямой загрузки файла в хранилище"""
        expires_at = datetime.now(UTC) + timedelta(seconds=PRESIGNED_URL_EXPIRES_IN)
        upload_id = uuid4()
        # 1. Создание уникального ключа
        extension = Path(request.filename).suffix.lower()
        unique_name = f"{upload_id}{extension}"
        storage_key = f"{request.folder}/{uploaded_by}/{unique_name}"

        upload = await self.upload_session_repo.create(
            UploadSession(
                id=upload_id,
                storage_key=storage_key,
                filename=request.filename,
                content_type=request.content_type,
                size_bytes=request.size_bytes,
                sha256=request.sha256,
                uploaded_by=uploaded_by,
                expires_at=expires_at,
            )
        )

        url = await self.storage.create_upload_url(
            storage_key=storage_key,
            content_type=request.content_type,
            expires_in=PRESIGNED_URL_EXPIRES_IN,
        )
        await self.session.commit()
        info = UploadInfo(url=url, expires_in=PRESIGNED_URL_EXPIRES_IN)  # pyright: ignore[reportArgumentType]
        return UploadResponse(id=upload.id, upload=info)

    async def complete_upload(
        self,
        upload_id: UUID,
        user_id: UUID,
    ) -> StoredObject:
        """Подтверждение загрузки файла"""
        if (upload := await self.upload_session_repo.read(upload_id)) is None:
            raise NotFoundError("Upload session not found")
        validate_upload_ownership(upload, user_id)
        if is_valid_upload_status_to_complete(upload):
            return upload.object  # pyright: ignore[reportAttributeAccessIssue]

        obj_meta = await self.storage.get_metadata(upload.storage_key)
        validate_uploaded_object(upload, obj_meta)

        stored_object = await self.stored_object_repo.get_by_hash(sha256=upload.sha256)
        if stored_object is None:
            stored_object = await self.stored_object_repo.create(
                StoredObject(
                    storage_key=upload.storage_key,
                    size_bytes=upload.size_bytes,
                    sha256=upload.sha256,
                    content_type=upload.content_type,
                )
            )
        upload.object_id = stored_object.id
        upload.status = UploadStatus.COMPLETED

        await self.session.flush()
        return stored_object

    async def create_presigned_download_url(
        self,
        stored_object_id: UUID,
    ) -> PresignedDownloadResponse:
        """Создание временной ссылки для скачивания файла"""

        # 1. Получение вложения из БД
        stored_object = await self.stored_object_repo.read(stored_object_id)
        if stored_object is None:
            raise NotFoundError(f"Attachment with ID {stored_object_id} not found")

        # 2. Генерация подписанного (временного) URL
        presigned_url = await self.storage.create_download_url(
            storage_key=stored_object.storage_key,
            expires_in=PRESIGNED_URL_EXPIRES_IN,
        )

        return PresignedDownloadResponse(
            download_url=presigned_url,
            storage_key=stored_object.storage_key,
            expires_in=PRESIGNED_URL_EXPIRES_IN,
        )
