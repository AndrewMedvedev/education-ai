import base64
import binascii
from hashlib import sha256
from uuid import UUID

from aiohttp import ClientError, ClientSession, ClientTimeout
from pydantic import BaseModel, Field

from src.media.application.dtos import CreateUploadDTO, UploadResponse
from src.shared.domain.exceptions import BadRequestError
from src.shared.infra.services.exceptions import SrvBaseError

from .services.client import SrvLLMRouterClient


class _ConfirmedUpload(BaseModel):
    storage_key: str = Field(min_length=1)


class MediaClient:
    def __init__(
        self,
        client: SrvLLMRouterClient,
        *,
        max_image_bytes: int = 20 * 1024 * 1024,
        upload_timeout: float = 120.0,
    ) -> None:
        if max_image_bytes <= 0:
            raise ValueError("max_image_bytes must be positive")
        if upload_timeout <= 0:
            raise ValueError("upload_timeout must be positive")

        self.client = client
        self._max_image_bytes = max_image_bytes
        self._upload_timeout = ClientTimeout(
            total=upload_timeout,
            connect=10.0,
            sock_read=60.0,
        )

    async def save_image(self, image: str, folder: str) -> str:
        """Загружает изображение в S3 через API модуля media."""
        content = self._decode_image(image)
        extension = self._detect_extension(content)

        request = CreateUploadDTO(
            filename=f"image.{extension}",
            content_type=f"image/{extension}",
            folder=folder,
            size_bytes=len(content),
            sha256=sha256(content).hexdigest(),
        )

        try:
            upload = await self._create_upload(request)
            await self._upload_content(upload, request.content_type, content)
            return await self._confirm_upload(upload.id)
        except (TimeoutError, ClientError) as error:
            # Не включаем str(error): он может содержать presigned URL.
            raise SrvBaseError(f"Media upload transport failed: {type(error).__name__}") from error

    def _decode_image(self, image: str) -> bytes:
        max_encoded_length = 4 * ((self._max_image_bytes + 2) // 3)

        if len(image) > max_encoded_length:
            raise BadRequestError("Image exceeds the allowed size")

        try:
            content = base64.b64decode(image, validate=True)
        except (ValueError, binascii.Error) as error:
            raise BadRequestError("Invalid image Base64") from error

        if not content:
            raise BadRequestError("Image must not be empty")

        if len(content) > self._max_image_bytes:
            raise BadRequestError("Image exceeds the allowed size")

        return content

    @staticmethod
    def _detect_extension(content: bytes) -> str:
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        if content.startswith(b"\xff\xd8\xff"):
            return "jpeg"
        if content.startswith((b"GIF87a", b"GIF89a")):
            return "gif"
        if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
            return "webp"

        raise BadRequestError("Unsupported image format")

    async def _create_upload(self, request: CreateUploadDTO) -> UploadResponse:
        async with (
            self.client._get_token_session() as session,
            session.post(
                "/api/v1/attachments/presigned-upload",
                json=request.model_dump(mode="json", by_alias=True),
            ) as response,
        ):
            if response.status != 200:
                raise SrvBaseError(f"Media presigned upload failed: HTTP {response.status}")

            return UploadResponse.model_validate(await response.json())

    async def _upload_content(
        self,
        upload: UploadResponse,
        content_type: str,
        content: bytes,
    ) -> None:
        headers = {"Content-Type": content_type, **upload.upload.headers}

        # Сессия без base_url и OAuth-заголовков backend.
        async with (
            ClientSession(timeout=self._upload_timeout) as session,
            session.request(
                method=upload.upload.method,
                url=str(upload.upload.url),
                data=content,
                headers=headers,
                allow_redirects=False,
            ) as response,
        ):
            if not 200 <= response.status < 300:
                raise SrvBaseError(
                    f"S3 image upload failed: HTTP {response.status}; upload_id={upload.id}"
                )

            await response.read()

    async def _confirm_upload(self, upload_id: UUID) -> str:
        async with (
            self.client._get_token_session() as session,
            session.post(
                f"/api/v1/attachments/confirm-upload/{upload_id}",
            ) as response,
        ):
            if response.status != 201:
                raise SrvBaseError(
                    f"Media confirm upload failed: HTTP {response.status}; upload_id={upload_id}"
                )

            result = _ConfirmedUpload.model_validate(await response.json())
            return result.storage_key
