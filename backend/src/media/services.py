from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.domain.exceptions import NotFoundError
from src.shared.utils.time import current_datetime

from .constants import PRESIGNED_URL_EXPIRES_IN
from .domain.entities import Attachment
from .domain.ports import AttachmentRepository, Storage
from .mappers import map_attachment_to_response
from .schemas import (
    AttachmentResponse,
    ConfirmUploadRequest,
    PresignedDownloadResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
)

# TODO @AndreyKosov: Добавить функционал сессий загрузки (pending upload). Использовать Redis для сессий  # ruff:ignore[line-too-long, line-contains-todo, missing-todo-link]


class AttachmentService:
    def __init__(
        self,
        session: AsyncSession,
        storage: Storage,
        repository: AttachmentRepository,
    ) -> None:
        """Инициализирует объект и сохраняет зависимости, необходимые для дальнейшей работы."""
        self.session = session
        self.storage = storage
        self.repository = repository

    async def create_presigned_upload_url(
        self,
        request: PresignedUploadRequest,
    ) -> PresignedUploadResponse:
        """Создание подписанного URL для прямой загрузки файла в хранилище"""

        # 1. Создание уникального ключа
        extension = Path(request.filename).suffix.lower()
        unique_name = f"{uuid4()}{extension}"
        storage_key = f"{request.folder}/{request.owner_id}/{unique_name}"

        # 2. Генерация подписанного URL для загрузки
        presigned_url = await self.storage.create_presigned_upload_url(
            storage_key=storage_key,
            content_type=request.content_type,
            expires_in=PRESIGNED_URL_EXPIRES_IN,
        )

        # 3. Формирование ответа
        return PresignedUploadResponse(
            upload_url=presigned_url,
            storage_key=storage_key,
            expires_in=PRESIGNED_URL_EXPIRES_IN,
        )

    async def confirm_upload(
        self,
        request: ConfirmUploadRequest,
        uploaded_by: UUID,
    ) -> AttachmentResponse:
        """Подтверждение загрузки файла"""

        # 1. Получение размера файла из хранилища
        file_info = await self.storage.get_file_info(request.storage_key)
        size_bytes = file_info["size"]
        uploaded_at = file_info.get("uploaded_at")
        if uploaded_at is None:
            uploaded_at = current_datetime()

        # 2. Создание доменной сущности вложения
        attachment = Attachment(
            original_filename=request.original_filename,
            mime_type=request.content_type,
            size_bytes=size_bytes,
            storage_key=request.storage_key,
            owner_id=request.owner_id,
            uploaded_at=uploaded_at,
            uploaded_by=uploaded_by,
        )
        await self.repository.create(attachment)
        await self.session.commit()

        # 3. Формирование ответа + получение preview для изображений
        return map_attachment_to_response(attachment)

    async def create_presigned_download_url(
        self, attachment_id: UUID
    ) -> PresignedDownloadResponse:
        """Создание временной ссылки для скачивания файла"""

        # 1. Получение вложения из БД
        attachment = await self.repository.read(attachment_id)
        if attachment is None:
            raise NotFoundError(f"Attachment with ID {attachment_id} not found")

        # 2. Генерация подписанного (временного) URL
        presigned_url = await self.storage.create_presigned_download_url(
            storage_key=attachment.storage_key, expires_in=PRESIGNED_URL_EXPIRES_IN
        )

        return PresignedDownloadResponse(
            download_url=presigned_url,
            storage_key=attachment.storage_key,
            expires_in=PRESIGNED_URL_EXPIRES_IN,
        )
