from typing import Any

from aiohttp import ClientSession, ClientTimeout

from src.media.schemas import ConfirmUploadRequest, PresignedUploadRequest
from src.shared.domain.exceptions import BadRequestError
from src.shared.infra.services import SrvBaseClient


class MediaClient:
    def __init__(self, client: SrvBaseClient) -> None:
        """Инициализирует объект и сохраняет зависимости, необходимые для дальнейшей работы."""
        self._client = client

    async def get_presigned_upload_url(
        self,
        schema: PresignedUploadRequest,
    ) -> dict[str, Any]:
        """Получает presigned upload url, чтобы вызывающий код работал через единый интерфейс."""
        async with self._client._get_token_session() as session:
            result = await session.post(
                url="/api/v1/attachments/presigned-upload",
                json=schema.model_dump(mode="json", exclude_none=True),
            )
            return await result.json()

    @staticmethod
    async def upload_file(
        file: bytes,
        presigned_url: str,
        content_type: str,
    ) -> None:
        async with (
            ClientSession(
                timeout=ClientTimeout(60),
            ) as session,
            session.put(
                presigned_url,
                data=file,
                headers={
                    "Content-Type": content_type,
                },
            ) as response,
        ):
            if 200 <= response.status < 300:
                return

            body = await response.text()

            raise BadRequestError(message=(f"S3 upload failed: HTTP {response.status}: {body}"))

    async def confirm_upload(
        self,
        schema: ConfirmUploadRequest,
    ) -> dict[str, Any]:
        """Подтверждает upload, чтобы завершить ранее начатую операцию."""
        async with self._client._get_token_session() as session:
            result = await session.post(
                url="/api/v1/attachments/confirm-upload",
                json=schema.model_dump(mode="json", exclude_none=True),
            )
        return await result.json()

    async def save_image(
        self,
        request: PresignedUploadRequest,
        file: bytes,
    ) -> str:
        """Сохраняет изображение, чтобы результат был доступен после завершения операции."""
        upload_url = await self.get_presigned_upload_url(schema=request)
        await self.upload_file(
            file=file,
            presigned_url=upload_url.get("upload_url"),  # pyright: ignore[reportArgumentType]
            content_type=request.content_type,
        )

        uploaded_file = await self.confirm_upload(
            schema=ConfirmUploadRequest(
                owner_id=request.owner_id,
                storage_key=upload_url.get("storage_key"),  # pyright: ignore[reportArgumentType]
                content_type=request.content_type,
                original_filename=request.filename,
            ),
        )
        return f"{uploaded_file["owner_id"]}/{uploaded_file["id"]}"
