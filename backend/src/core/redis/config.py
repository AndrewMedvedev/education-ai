from pydantic_settings import BaseSettings, SettingsConfigDict

from ..settings import ENV_FILE  # ruff: ignore[unused-import]


class RedisConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = "<PASSWORD>"

    @property
    def url(self) -> str:
        return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"


redis_config = RedisConfig()
