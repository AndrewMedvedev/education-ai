from pydantic_settings import BaseSettings, SettingsConfigDict

from ..settings import ENV_FILE  # noqa: F401


class QdrantConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QDRANT_")

    host: str = "localhost"
    port: int = 6333
    api_key: str = "<PASSWORD>"
    index_name: str = "main-index"

    @property
    def url(self) -> str:
        """Выполняет действие `url`, чтобы поддержать основной сценарий модуля."""
        return f"http://{self.host}:{self.port}"


qdrant_config = QdrantConfig()
