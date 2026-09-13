from typing import Any, BinaryIO, Protocol

from collections.abc import AsyncIterator
from uuid import UUID

from src.shared.application.repos import Repository

from .entities import Attachment


class AttachmentRepository(Repository[Attachment]):
    async def get_by_storage_key(self, storage_key: str) -> Attachment | None:
        """Получение вложения по уникальному ключу объекта в хранилище"""

    async def get_by_owner(self, owner_type: str, owner_id: UUID) -> list[Attachment]:
        """Получение прикреплённых вложений для сущности"""


class Storage(Protocol):
    async def upload(self, file: BinaryIO, storage_key: str, content_type: str) -> None:
        """Загружает файл в хранилище"""

    async def download(self, storage_key: str) -> BinaryIO:
        """
        Скачивает файл целиком в память.
        Использовать осторожно для больших файлов.
        """

    async def upload_stream(
        self, chunks: AsyncIterator[bytes], storage_key: str, content_type: str
    ) -> None:
        """
        Потоковая загрузка файла в хранилище (рекомендуемо для больших файлов)
        """

    async def download_stream(
        self, storage_key: str, chunk_size: int = 4 * 1024 * 1024
    ) -> AsyncIterator[bytes]:
        """
        Потоковая загрузка файла (рекомендуется для больших файлов).
        """

    async def delete(self, storage_key: str) -> None:
        """Удаление файла"""

    async def create_presigned_upload_url(
        self, storage_key: str, content_type: str, expires_in: int = 3600
    ) -> str:
        """
        Генерирует подписанный URL для прямой загрузки с фронтенда
        """

    async def create_presigned_download_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """
        Возвращает публичный (или временный) URL для просмотра файла.
        """

    async def get_file_info(self, storage_key: str) -> dict[str, Any]:
        """Получение информации о загруженном файле"""
