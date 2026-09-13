from pydantic_settings import BaseSettings, SettingsConfigDict

from ..settings import ENV_FILE  # ruff: ignore[unused-import]


class QdrantConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QDRANT_")

    host: str = "localhost"
    port: int = 6333
    api_key: str = "<PASSWORD>"

    @property
    def url(self) -> str:
        """Выполняет действие `url`, чтобы поддержать основной сценарий модуля."""
        return f"http://{self.host}:{self.port}"


qdrant_config = QdrantConfig()
