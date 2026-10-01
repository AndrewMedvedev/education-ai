from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.media.domain.vo import UploadStatus
from src.shared.infra.database.types import DatetimeTz, StrUnique


class UploadSessionOrm(Base):
    """Сессия прямой загрузки файла в S3."""

    __tablename__ = "upload_sessions"

    storage_key: Mapped[StrUnique]
    filename: Mapped[str]
    content_type: Mapped[str]
    size_bytes: Mapped[int]
    sha256: Mapped[str]
    uploaded_by: Mapped[UUID]
    status: Mapped[UploadStatus] = mapped_column(default=UploadStatus.PENDING)
    expires_at: Mapped[DatetimeTz]
    object_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stored_objects.id", ondelete="RESTRICT"),
        nullable=True,
    )

    object: Mapped[StoredObjectOrm | None] = relationship()


class StoredObjectOrm(Base):
    """
    Физически загруженный объект в хранилище.
    Если такой объект существует, то файл гарантировано загружен в S3,
    его размер и checksum подтверждены.
    """

    __tablename__ = "stored_objects"

    storage_key: Mapped[StrUnique]
    size_bytes: Mapped[int]
    sha256: Mapped[str]
    content_type: Mapped[str]

    __table_args__ = (
        UniqueConstraint("sha256", "size_bytes", name="uq_stored_object_sha256_size"),
    )
