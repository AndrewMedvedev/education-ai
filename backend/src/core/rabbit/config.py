from pydantic_settings import BaseSettings, SettingsConfigDict

from ..settings import ENV_FILE  # ruff: ignore[unused-import]


class RabbitConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RABBIT_")

    host: str = "localhost"
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    virtualhost: str = "/"

    exchange: str = "app.events"

    heartbeat: int = 30
    connection_timeout: float = 10.0

    @property
    def uri(self) -> str:
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/{self.virtualhost.lstrip('/')}"


rabbit_config = RabbitConfig()
