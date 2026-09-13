from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ...shared.domain.entities import Entity
from ...shared.domain.exceptions import InvariantViolationError
from ..constants import DOCUMENT_MIME_TYPES, MAX_FILENAME_LENGTH


@dataclass(kw_only=True)
class Attachment(Entity):
    """
    Вложение (файл), который может быть прикреплён к тикету, комментарию,
    контрагенту, пользователю и т.д.
    """

    original_filename: str
    mime_type: str
    size_bytes: int
    storage_key: str
    owner_id: UUID
    uploaded_at: datetime
    uploaded_by: UUID

    def __post_init__(self) -> None:
        # 1. Валидация оригинального имени файла
        """Проверяет и нормализует состояние объекта сразу после создания dataclass."""
        if not self.original_filename or len(self.original_filename.strip()) < 1:
            raise ValueError("Original filename cannot be empty")
        if len(self.original_filename) > MAX_FILENAME_LENGTH:
            raise ValueError(f"Original filename too long (max {MAX_FILENAME_LENGTH} characters)")

        # 2. Проверка размера файла
        if self.size_bytes < 0:
            raise InvariantViolationError("File size cannot be negative")

    @property
    def extension(self) -> str:
        """Расширение файла"""

        return self.original_filename.split(".")[-1].lower()

    @property
    def is_image(self) -> bool:
        """Является ли изображением"""

        return self.mime_type.startswith("image/")

    @property
    def is_document(self) -> bool:
        """Является ли документом"""

        return self.mime_type in DOCUMENT_MIME_TYPES
