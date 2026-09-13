from pydantic_settings import BaseSettings, SettingsConfigDict

from ..settings import ENV_FILE  # ruff: ignore[unused-import]


class MailConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MAIL_")

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_use_tls: bool = False
    smtp_user: str = ""
    smtp_password: str = ""
    default_from_email: str = "diocon@mail.ru"
    support_email: str = "diocon.support@mail.ru"


mail_config = MailConfig()
