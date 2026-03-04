from typing import Literal

from pathlib import Path

import pytz
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

TIMEZONE = pytz.timezone("Europe/Moscow")
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
CHROMA_PATH = BASE_DIR / ".chroma"
TEMPLATES_DIR = BASE_DIR / "templates"

load_dotenv(ENV_PATH)


class TelegramSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TELEGRAM_")

    bot_token: str = "<BOT TOKEN>"
    webhook_path: str = "/hook"


class YandexCloudSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="YANDEX_CLOUD_")

    folder_id: str = "<FOLDER_ID>"
    api_key: str = "<APIKEY>"
    base_url: str = "https://llm.api.cloud.yandex.net/v1"

    @property
    def gemma_3_27b_it(self) -> str:
        return f"gpt://{self.folder_id}/gemma-3-27b-it/latest"

    @property
    def aliceai_llm(self) -> str:
        return f"gpt://{self.folder_id}/aliceai-llm"

    @property
    def qwen3_235b(self) -> str:
        return f"gpt://{self.folder_id}/qwen3-235b-a22b-fp8/latest"

    @property
    def yandexgpt_rc(self) -> str:
        return f"gpt://{self.folder_id}/yandexgpt/rc"


class DeepSeekSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DEEPSEEK_")

    api_key: str = "<APIKEY>"
    base_url: str = "https://api.deepseek.com"

    @property
    def deepseek_chat(self) -> str:
        return "deepseek-chat"


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POSTGRES_")

    host: str = "postgres"
    port: int = 5432
    user: str = "<USER>"
    password: str = "<PASSWORD>"
    db: str = "<DB>"
    driver: Literal["asyncpg"] = "asyncpg"

    @property
    def sqlalchemy_url(self) -> str:
        return f"postgresql+{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_")

    url: str = "http://localhost:8000"
    port: int = 8000


class Settings(BaseSettings):
    telegram: TelegramSettings = TelegramSettings()
    yandexcloud: YandexCloudSettings = YandexCloudSettings()
    deepseek: DeepSeekSettings = DeepSeekSettings()
    postgres: PostgresSettings = PostgresSettings()
    app: AppSettings = AppSettings()


settings = Settings()
