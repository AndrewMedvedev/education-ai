from typing import Any

from datetime import timedelta
from enum import StrEnum

from pydantic import SecretStr

from src.core.commons import get_expiration_timestamp
from src.core.entities.user import User
from src.core.errors import ConflictError, ForbiddenError, UnauthorizedError
from src.infra.db.repos import UserRepository
from src.settings import settings
from src.utils.secutiry import get_password_hash, issue_token, verify_password

from ..schemas import Token, TokensPair, UserRegister, UserResponse


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


def create_tokens_pair(payload: dict[str, Any]) -> TokensPair:
    """Создание пары JWT токенов 'access' и 'refresh'"""

    access_token_expires_in = timedelta(minutes=settings.jwt.user_access_token_expires_in_minutes)
    refresh_token_expires_in = timedelta(days=settings.jwt.user_refresh_token_expires_in_days)
    access_token = issue_token(
        token_type=TokenType.ACCESS, payload=payload, expires_in=access_token_expires_in,
    )
    refresh_token = issue_token(
        token_type=TokenType.REFRESH, payload=payload, expires_in=refresh_token_expires_in
    )
    return TokensPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=get_expiration_timestamp(access_token_expires_in),
    )


def create_access_token(payload: dict[str, Any]) -> Token:
    """Создание 'access' токена"""

    expires_in = timedelta(days=settings.jwt.guest_access_token_expires_in_days)
    access_token = issue_token(token_type=TokenType.ACCESS, payload=payload, expires_in=expires_in)
    return Token(access_token=access_token, expires_at=get_expiration_timestamp(expires_in))


class AuthService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def register(self, data: UserRegister) -> UserResponse:
        """Регистрация пользователя"""

        user = await self.repository.get_by_email(data.email)
        if user is not None:
            raise ConflictError(f"Email {data.email} already registered!")
        password_hash = get_password_hash(data.password)
        user = User(
            username=data.username,
            full_name=data.full_name,
            email=data.email,
            password_hash=SecretStr(password_hash),
            role=data.role,
        )
        await self.repository.create(user)
        return UserResponse.model_validate(user)

    async def authenticate(self, username: str, password: str) -> TokensPair:
        """Аутентификация пользователя"""

        user = await self.repository.get_by_username(username)
        if not verify_password(password, user.password_hash.get_secret_value()):
            raise ForbiddenError("Invalid credentials!")
        if user is None:
            raise UnauthorizedError("Registration required!")
        return create_tokens_pair({
            "sub": str(user.id), "username": user.username, "email": user.email, "role": user.role
        })
