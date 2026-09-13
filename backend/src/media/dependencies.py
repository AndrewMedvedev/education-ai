from typing import Annotated

from fastapi import Depends

from src.core.settings import settings
from src.shared.dependencies.database import DBSession

from .domain.ports import AttachmentRepository, Storage
from .infra.repo import SqlAttachmentRepository
from .infra.s3 import S3Storage
from .services import AttachmentService

# def get_storage() -> Storage:
#     """Получает storage, чтобы вызывающий код работал через единый интерфейс."""
#     return S3Storage(
#         access_key=settings.yandex_cloud.access_key_id,
#         secret_key=settings.yandex_cloud.secret_access_key,
#         endpoint_url=settings.yandex_cloud.endpoint_url,
#         bucket_name=S3_BUCKET_NAME,
#     )


def get_storage() -> Storage:
    """Получает storage, чтобы вызывающий код работал через единый интерфейс."""
    return S3Storage(
        access_key=settings.s3.access_key,
        secret_key=settings.s3.secret_key,
        endpoint_url=settings.s3.endpoint_url,
        bucket_name=settings.s3.bucket,
    )


def get_attachment_repo(session: DBSession) -> SqlAttachmentRepository:
    """Получает attachment repo, чтобы вызывающий код работал через единый интерфейс."""
    return SqlAttachmentRepository(session)


def get_attachment_service(
    session: DBSession,
    storage: Storage = Depends(get_storage),
    repository: AttachmentRepository = Depends(get_attachment_repo),
) -> AttachmentService:
    """Получает attachment service, чтобы вызывающий код работал через единый интерфейс."""
    return AttachmentService(session=session, storage=storage, repository=repository)


AttachmentRepoDep = Annotated[AttachmentRepository, Depends(get_attachment_repo)]
AttachmentServiceDep = Annotated[AttachmentService, Depends(get_attachment_service)]
