from uuid import UUID

from fastapi import APIRouter, status

from src.iam.dependencies import CurrentIdentity
from src.shared.domain.exceptions import NotFoundError

from ...application.dtos import (
    CreateUploadDTO,
    PresignedDownloadResponse,
    UploadResponse,
)
from ...dependencies.base import StoredObjectRepoDep
from ...dependencies.services import AttachmentServiceDep
from ...domain.entities import StoredObject

router = APIRouter(prefix="/attachments", tags=["Медиа контент"])


@router.post(
    path="/presigned-upload",
    status_code=status.HTTP_200_OK,
    summary="Получить presigned URL для загрузки",
    description="""\
    Создаёт подписанный URL на стороне хранилища (S3)
    для прямой загрузки файла с клиентской части.
    """,
)
async def create_presigned_upload_url(
    identity: CurrentIdentity,
    request: CreateUploadDTO,
    service: AttachmentServiceDep,
) -> UploadResponse:
    """Создаёт presigned upload url и инкапсулирует правила этой операции."""
    return await service.create_presigned_upload_url(request, uploaded_by=identity.id)


@router.post(
    path="/confirm-upload/{upload_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Подтвердить загрузку и создать вложение",
)
async def confirm_upload(
    identity: CurrentIdentity,
    upload_id: UUID,
    service: AttachmentServiceDep,
) -> StoredObject:
    """Подтверждает upload, чтобы завершить ранее начатую операцию."""
    return await service.complete_upload(upload_id, user_id=identity.id)


@router.get(
    path="/{stored_object_id}/presigned-download",
    status_code=status.HTTP_200_OK,
    summary="Получить presigned URL для скачивания",
)
async def get_presigned_download_url(
    _identity: CurrentIdentity,
    stored_object_id: UUID,
    service: AttachmentServiceDep,
) -> PresignedDownloadResponse:
    """Получает presigned download url, чтобы вызывающий код работал через единый интерфейс."""
    return await service.create_presigned_download_url(stored_object_id)


@router.get(
    path="/{stored_object_id}",
    status_code=status.HTTP_200_OK,
    summary="Получение информации и файле",
)
async def get_attachment(
    _identity: CurrentIdentity,
    stored_object_id: UUID,
    repository: StoredObjectRepoDep,
) -> StoredObject:
    """Получает attachment, чтобы вызывающий код работал через единый интерфейс."""
    attachment = await repository.read(stored_object_id)
    if attachment is None:
        raise NotFoundError(f"Attachment with ID {stored_object_id} not found")
    return attachment
