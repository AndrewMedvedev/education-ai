from pydantic_settings import BaseSettings, SettingsConfigDict

from ..settings import ENV_FILE  # ruff: ignore[unused-import]


class EmbeddingsConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EMBEDDINGS_")

    base_url: str = "http://localhost:7997/"
    model_name: str = "deepvk/USER-bge-m3"
    dimensions: int = 1024


class RerankersConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RERANKERS_")

    base_url: str = "http://localhost:7998"
    model_name: str = "BAAI/bge-reranker-v2-m3"


embeddings_config = EmbeddingsConfig()
rerankers_config = RerankersConfig()
