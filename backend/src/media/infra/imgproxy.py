import base64
import hashlib
import hmac
from urllib.parse import quote

from src.core.settings import settings


class ImgProxyService:
    def __init__(
        self,
        base_url: str,
        bucket_name: str,
        key: str,
        salt: str,
    ) -> None:
        """Инициализирует объект и сохраняет зависимости, необходимые для дальнейшей работы."""
        self.base_url = base_url
        self.bucket_name = bucket_name
        self.key = key
        self.salt = salt

    def get_url(
        self,
        storage_key: str,
        width: int = 200,
        height: int = 200,
        resize_type: str = "fit",
        img_format: str = "webp",
        quality: int = 85,
    ) -> str:
        """
        Генерирует URL через Imgproxy
        Пример: /rs:200x200/fit/plain/local:///avatars/users/123.jpg@webp
        """

        # 1. Базовый путь обработки + указываем источник
        source = f"s3://{self.bucket_name}/{storage_key}"
        encoded_source = quote(source, safe="/:")
        processing = f"rs:{width}x{height}/{resize_type}"

        # 2. Полный путь к файлу
        path = f"/{processing}/plain/{encoded_source}@{img_format}"

        # 3. Добавление качества изображения
        if quality:
            path += f"/q:{quality}"

        # 4. Добавление подписи
        signature = self._sign(path)
        signed_path = f"/{signature}{path}"

        return f"{self.base_url}{signed_path}"

    def _sign(self, path: str) -> str:
        """
        Создание секретной подписи (возвращает только подпись)
        для защиты от несанкционированной работы с изображениями.
        """

        if self.key is None and self.salt is None:
            return "unsafe"

        key_bytes = bytes.fromhex(self.key)
        salt_bytes = bytes.fromhex(self.salt)

        digest = hmac.new(key_bytes + salt_bytes, path.encode("utf-8"), hashlib.sha256).digest()
        signature = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

        return f"s:{signature}"

    def avatar(self, storage_key: str, size: int = 200) -> str:
        """Аватарка — квадрат, обычно с обрезкой"""

        return self.get_url(
            storage_key=storage_key,
            width=size,
            height=size,
            resize_type="fill",
            img_format="webp",
        )

    def preview(self, storage_key: str, width: int = 400) -> str:
        """Превью для документов/изображений"""

        return self.get_url(
            storage_key=storage_key,
            width=width,
            height=0,
            resize_type="fit",
            img_format="webp",
        )


imgproxy_service = ImgProxyService(
    base_url=settings.imgproxy.url,
    bucket_name="",
    key=settings.imgproxy.key,
    salt=settings.imgproxy.salt,
)
