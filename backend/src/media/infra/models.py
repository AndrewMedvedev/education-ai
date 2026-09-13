from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class AttachmentOrm(Base):
    __tablename__ = "attachments"

    original_filename: Mapped[str]
    mime_type: Mapped[str]
    size_bytes: Mapped[int]
    storage_key: Mapped[str] = mapped_column(unique=True)
    owner_id: Mapped[UUID]
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    uploaded_by: Mapped[UUID]
