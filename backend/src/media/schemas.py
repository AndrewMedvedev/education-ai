from typing import TypedDict

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, PositiveInt


class FileInfo(TypedDict):
    """Информация о файле полученная из хранилища"""

    size: int
    content_type: str
    uploaded_at: datetime


class PresignedUploadRequest(BaseModel):
    """Запрос для загрузки файла"""

    filename: str = Field(..., min_length=1, max_length=255, description="Имя файла")
    folder: str = Field(..., min_length=1, max_length=255, description="Имя папки")

    content_type: str = Field(
        ...,
        pattern=r"^[\w\-]+/[\w\-\.]+$",
        description="Тип контента файла",
        examples=["application/pdf"],
    )

    owner_id: UUID = Field(..., description="ID сущности, которой принадлежит файл")


class PresignedUploadResponse(BaseModel):
    """API схема ответа для подписанного URL"""

    upload_url: str = Field(..., description="URL адрес на который нужно загрузить файл")
    storage_key: str = Field(..., description="Уникальный ключ загружаемого объекта")
    expires_in: PositiveInt = Field(
        ..., description="Временной промежуток в формате Timestamp, через который истекает ссылка"
    )


class ConfirmUploadRequest(BaseModel):
    """Подтверждение загрузки"""

    storage_key: str = Field(
        ..., min_length=1, max_length=255, description="Уникальный ключ загруженного объекта"
    )
    original_filename: str = Field(..., description="Оригинальное имя файла")
    content_type: str = Field(
        ...,
        pattern=r"^[\w\-]+/[\w\-\.]+$",
        description="Тип контента файла",
        examples=["application/pdf"],
    )
    owner_id: UUID = Field(..., description="ID сущности, которой принадлежит файл")


class AttachmentResponse(BaseModel):
    """API схема ответа для вложения"""

    id: UUID = Field(..., description="Уникальный ID файла")
    original_filename: str = Field(..., description="Оригинальное имя файла")
    mime_type: str = Field(..., description="Mime тип файла")
    size_bytes: PositiveInt = Field(..., description="Размер файла в байтах")
    storage_key: str = Field(..., description="Уникальный ключ объекта в хранилище")

    owner_id: UUID = Field(..., description="ID сущности, которой принадлежит вложение")
    uploaded_by: UUID = Field(..., description="ID пользователя, который загрузил файл")
    uploaded_at: datetime = Field(..., description="Дата загрузки объекта в хранилище")


class PresignedDownloadResponse(BaseModel):
    """API ответ для скачивая файла напрямую из хранилища"""

    download_url: str = Field(..., description="Временный URL для скачивания файла")
    storage_key: str = Field(..., description="Уникальный ключ загружаемого объекта")
    expires_in: PositiveInt = Field(
        ..., description="Временной промежуток в формате Timestamp, через который истекает ссылка"
    )
