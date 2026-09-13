from pathlib import Path

import pytz  # type: ignore  # ruff:ignore[blanket-type-ignore]
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

TIMEZONE = "Asia/Yekaterinburg"
timezone = pytz.timezone(TIMEZONE)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

ENV_FILE = BASE_DIR / ".env"

ENV_DEV_FILE = BASE_DIR / ".env.dev"  # Среда для разработки

load_dotenv(ENV_FILE)

INSTALLED_MODULES: tuple[str, ...] = (  # Добавь сюда модуль который готов к использованию
    "iam",
    "courses",
    "llm_router",
    "organization",
    "media",
)
TEMPLATES_DIR = BASE_DIR / "templates"
# Имя основного S3 бакета


class JWTConfig(BaseSettings):
    algorithm: str = "HS256"
    authentication_token_expires_in_minutes: int = 2
    access_token_expires_in_minutes: int = 15
    refresh_token_expires_in_days: int = 30


class LangSmithConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LANGSMITH_")
    tracing: bool = True
    endpoint: str = ""
    api_key: str = ""
    project: str = ""


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_")

    port: int = 8000
    version: str = Field(description="Актуальная версия приложения.", examples=["12.5.1"])

    cors_origins: list[str] = ["http://localhost:3000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]


class SuperAdminConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SUPER_ADMIN_")

    email: str = "admin@admin.com"
    password: str = "admin"
    username: str = "admin"
    full_name: str = Field(
        default="Админов Админ Админович", description="ФИО для нормального отображения в системе."
    )


class Settings(BaseSettings):
    secret_key: str = "<SECRET_KEY>"
    frontend_url: str = "http://localhost:3000"
    base_llm_router_url: str = "http://localhost:8000/api/v1/"
    attachments_url: str = "http://localhost:8000/api/v1/attachments/"
    chromium_ws_endpoint: str = "ws://localhost:3000/playwright/chromium"
    text_ai_model: str = "gemini-2.5-flash-lite"
    image_ai_model: str = "gpt-image-2"


jwt_config = JWTConfig()
langsmith_config = LangSmithConfig()
app_config = AppConfig()  # pyright: ignore[reportCallIssue]
super_admin_config = SuperAdminConfig()
settings = Settings()
