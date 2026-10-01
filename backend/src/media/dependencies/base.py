from typing import Annotated

from fastapi import Depends

from src.core.s3 import s3_config
from src.shared.dependencies.database import DBSession

from ..application.repos import Storage
from ..infra.database.repos.s3 import S3Client
from ..infra.database.repos.stored_object import SqlStoredObjectRepository
from ..infra.database.repos.upload_session import SqlUploadSessionRepository


def get_storage() -> Storage:
    """Получает storage, чтобы вызывающий код работал через единый интерфейс."""
    return S3Client(s3_config)


def get_upload_session_repo(session: DBSession) -> SqlUploadSessionRepository:
    """Получает upload session repo, чтобы вызывающий код работал через единый интерфейс."""
    return SqlUploadSessionRepository(session)


def get_object_repo(session: DBSession) -> SqlStoredObjectRepository:
    """Получает object repo, чтобы вызывающий код работал через единый интерфейс."""
    return SqlStoredObjectRepository(session)


UploadSessionRepoDep = Annotated[SqlUploadSessionRepository, Depends(get_upload_session_repo)]
StoredObjectRepoDep = Annotated[SqlStoredObjectRepository, Depends(get_object_repo)]
StorageRepoDep = Annotated[Storage, Depends(get_storage)]
