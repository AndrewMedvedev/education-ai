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


class Settings(BaseSettings):
    bot: BotSettings = BotSettings()


settings: Final[Settings] = Settings()
