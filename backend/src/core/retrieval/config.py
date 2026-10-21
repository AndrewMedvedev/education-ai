from pydantic_settings import BaseSettings, SettingsConfigDict

from ..settings import ENV_FILE  # noqa: F401


class EmbeddingsConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EMBEDDINGS_")

    base_url: str = "http://localhost:7997/"
    model_name: str = "qwen3-embedding-8b"
    dimensions: int = 4096


class RerankersConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RERANKERS_")

    base_url: str = "http://localhost:7998"
    model_name: str = "rerank-3-lite"


embeddings_config = EmbeddingsConfig()
rerankers_config = RerankersConfig()
