from typing import Annotated, Literal

from dataclasses import dataclass

from fastapi import Form
from pydantic import BaseModel, Field, NonNegativeInt


@dataclass(frozen=True, slots=True)
class OAuthCredentials:
    """Учётные данные для сервисного аккаунта."""

    grant_type: Annotated[Literal["client_credentials"], Form(description="Тип авторизации.")]
    client_id: Annotated[str, Form(description="Идентификатор сервисного аккаунта.")]
    client_secret: Annotated[str, Form(description="Секретный ключ.")]


class OAuthTokenResponse(BaseModel):
    access_token: str = Field(description="JWT токен для аутентификации.")
    token_type: Literal["Bearer"] = Field(default="Bearer", frozen=True)
    expires_at: NonNegativeInt = Field(description="Истекает в (timestamp).")
