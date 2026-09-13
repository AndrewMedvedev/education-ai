from pydantic_settings import BaseSettings, SettingsConfigDict

from ..settings import ENV_FILE  # ruff: ignore[unused-import]


class ProxyApiConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROXY_API_")

    key: str = "<API_KEY>"
    base_url: str = "https://openai.api.proxyapi.ru/v1"


class AITunnelConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AITUNNEL_")

    key: str = "<API_KEY>"
    base_url: str = "https://api.aitunnel.ru/v1"


class YandexCloudConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="YANDEX_CLOUD_")

    folder_id: str = "<FOLDER_ID>"
    api_key: str = "<API_KEY>"
    base_url: str = "https://llm.api.cloud.yandex.net/v1"

    access_key_id: str = "<ACCESS_KEY_ID>"
    secret_access_key: str = "<SECRET_ACCESS_KEY>"
    endpoint_url: str = "https://storage.yandexcloud.net/"


proxy_api_config = ProxyApiConfig()
aitunnel_config = AITunnelConfig()
yandex_cloud_config = YandexCloudConfig()
