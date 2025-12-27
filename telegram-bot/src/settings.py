from typing import Final

from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BOT_")

    token: str = "<TOKEN>"


class YandexCloudSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="YANDEX_CLOUD_")

    folder_id: str = "<FOLDER_ID>"
    apikey: str = "<APIKEY>"
    base_url: str = "https://llm.api.cloud.yandex.net/v1"

    @property
    def gemma_3_27b_it(self) -> str:
        return f"gpt://{self.folder_id}/gemma-3-27b-it/latest"

    @property
    def yandexgpt_rc(self) -> str:
        return f"gpt://{self.folder_id}/gemma-3-27b-it/latest"


class Settings(BaseSettings):
    bot: BotSettings = BotSettings()
    yandexcloud: YandexCloudSettings = YandexCloudSettings()


settings: Final[Settings] = Settings()
