from pydantic_settings import BaseSettings, SettingsConfigDict

from ..settings import ENV_FILE  # ruff: ignore[unused-import]


class S3Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="S3_")

    service_name: str = "s3"
    access_key: str = ""
    secret_key: str = ""
    endpoint_url: str = "http://localhost:9000"
    bucket: str = "diocon-courses-backups"


s3_config = S3Config()
