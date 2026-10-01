from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ...shared.domain.entities import Entity
from .vo import UploadStatus


@dataclass(kw_only=True)
class StoredObject(Entity):
    storage_key: str
    size_bytes: int
    sha256: str
    content_type: str


@dataclass(kw_only=True)
class UploadSession(Entity):
    storage_key: str
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    uploaded_by: UUID
    status: UploadStatus = UploadStatus.PENDING
    expires_at: datetime
    object_id: UUID | None = None
