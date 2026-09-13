from pydantic import Field, HttpUrl, NonNegativeFloat, NonNegativeInt
from pydantic_settings import BaseSettings


class SrvBaseConfig(BaseSettings):
    base_url: HttpUrl = Field(
        description="Базовый URL адрес без слешей.",
        examples=["http://some-service.example"],
    )
    timeout: NonNegativeFloat = Field(default=300.0, description="Таймаут в миллисекундах.")
    keepalive_timeout: NonNegativeFloat = Field(
        default=30.0, description="Время жизни простаивающего соединения."
    )

    client_id: str
    client_secret: str

    token_rotate_margin: NonNegativeFloat = Field(
        default=30.0,
        description="За сколько секунд до истечения обновить access token.",
    )

    pool_limit: NonNegativeInt = Field(default=100, description="Ограничение пула соединений.")
    ttl_dns: NonNegativeInt = Field(default=300, description="Кеширование DNS в секундах.")
