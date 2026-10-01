from typing import BinaryIO, Protocol

from collections.abc import AsyncIterator
from uuid import UUID

from src.shared.application.repos import Repository

from ..domain.entities import StoredObject, UploadSession
from .dtos import ObjectMeta


class StoredObjectRepository(Repository[StoredObject]):
    async def get_by_storage_key(self, storage_key: str) -> StoredObject | None:
        """Получение вложения по уникальному ключу объекта в хранилище"""

    async def get_by_hash(self, sha256: str) -> StoredObject | None:
        """Получение вложения по уникальному ключу объекта в хранилище"""


class UploadSessionRepository(Repository[UploadSession]):
    async def update(self, storage_key: str, **kwargs) -> UploadSession | None: ...

    async def get_by_storage_key(self, storage_key: str) -> UploadSession | None:
        """Получение вложения по уникальному ключу объекта в хранилище"""

    async def get_by_owner(self, uploaded_by: UUID) -> list[UploadSession]: ...


class AsyncReadable(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


class Storage(Protocol):
    async def upload(
        self,
        file: BinaryIO,
        storage_key: str,
        content_type: str,
    ) -> None:
        """Загружает файл в хранилище."""
        ...

    async def delete(self, storage_key: str) -> None:
        """Удаляет файл из хранилища."""
        ...

    async def create_upload_url(
        self,
        storage_key: str,
        content_type: str,
        checksum: str | None = None,
        expires_in: int = 3600,
    ) -> str:
        """Генерирует подписанный URL для прямой загрузки с фронтенда."""
        ...

    async def create_download_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Возвращает временный URL для скачивания файла."""
        ...

    async def get_metadata(self, storage_key: str) -> ObjectMeta:
        """Получает метаданные загруженного файла."""
        ...

    async def upload_stream(
        self,
        file_stream: AsyncReadable,
        storage_key: str,
        mime_type: str,
        chunk_size: int = 5 * 1024 * 1024,
    ) -> None:
        """Потоковая загрузка файла в хранилище."""
        ...

    def download_stream(
        self,
        storage_key: str,
        chunk_size: int = 5 * 1024 * 1024,
    ) -> AsyncIterator[bytes]:
        """Потоковое чтение файла из хранилища."""
        ...
