# pyright: reportArgumentType=false

from typing import Annotated

from fastapi import Depends

from src.shared.dependencies.database import DBSession

from ..application.services import AttachmentService
from .base import StorageRepoDep, StoredObjectRepoDep, UploadSessionRepoDep


def get_attachment_service(
    session: DBSession,
    storage: StorageRepoDep,
    upload_session_repo: UploadSessionRepoDep,
    stored_object_repo: StoredObjectRepoDep,
) -> AttachmentService:
    """Получает attachment service, чтобы вызывающий код работал через единый интерфейс."""
    return AttachmentService(
        session=session,
        storage=storage,
        upload_session_repo=upload_session_repo,
        stored_object_repo=stored_object_repo,
    )


AttachmentServiceDep = Annotated[AttachmentService, Depends(get_attachment_service)]
