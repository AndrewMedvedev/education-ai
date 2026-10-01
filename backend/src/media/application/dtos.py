from typing import Literal

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, PositiveInt
from pydantic.alias_generators import to_camel

from ..infra.types import FilePathStr, Sha256Str


class CreateUploadDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    filename: FilePathStr
    content_type: str = Field(
        description="MIME-тип загружаемого файла",
        examples=["image/png", "plain/text"],
    )
    folder: str = Field(description="Папка для хранения файла")
    size_bytes: PositiveInt = Field(description="Размер файла в байтах")
    sha256: Sha256Str


class UploadInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    url: HttpUrl = Field(description="Временный URL для прямой загрузки")
    method: Literal["PUT"] = "PUT"
    headers: Mapping[str, str] = Field(default_factory=dict, description="Необходимые заголовки")
    expires_in: PositiveInt = Field(description="Время действия в секундах")


class UploadResponse(BaseModel):
    id: UUID = Field(description="Идентификатор сессии загрузки")
    upload: UploadInfo = Field(description="Информация для прямой загрузки файла в S3")


class ObjectMeta(BaseModel):
    size: int
    content_type: str
    last_modified: datetime
    checksum: str | None = None


class ConfirmUploadRequest(BaseModel):
    """Подтверждение загрузки"""

    storage_key: str = Field(
        ..., min_length=1, max_length=255, description="Уникальный ключ загруженного объекта"
    )

    checksum: str = Field(..., description="Хеш-сумма файла")


class PresignedDownloadResponse(BaseModel):
    """API ответ для скачивая файла напрямую из хранилища"""

    download_url: str = Field(..., description="Временный URL для скачивания файла")
    storage_key: str = Field(..., description="Уникальный ключ загружаемого объекта")
    expires_in: PositiveInt = Field(
        ..., description="Временной промежуток в формате Timestamp, через который истекает ссылка"
    )
