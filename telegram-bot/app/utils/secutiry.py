from typing import Any

import logging
from datetime import timedelta
from uuid import uuid4

import jwt
from passlib.context import CryptContext

from app.core.commons import current_datetime
from app.core.errors import UnauthorizedError
from app.settings import settings

# Хеширование паролей
MEMORY_COST = 100  # Размер выделяемой памяти в mb
TIME_COST = 2
PARALLELISM = 2
SALT_SIZE = 16
ROUNDS = 14  # Количество раундов для хеширования

logger = logging.getLogger(__name__)

pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    default="argon2",
    argon2__memory_cost=MEMORY_COST,
    argon2__time_cost=TIME_COST,
    argon2__parallelism=PARALLELISM,
    argon2__salt_size=SALT_SIZE,
    bcrypt__rounds=ROUNDS,
    deprecated="auto"
)


def hash_secret(secret: str) -> str:
    return pwd_context.hash(secret)


def verify_secret(plain_secret: str, hashed_secret: str) -> bool:
    """Сверяет ожидаемый пароль с хэшем пароля"""

    return pwd_context.verify(plain_secret, hashed_secret)


def issue_token(token_type: str, payload: dict[str, Any], expires_in: timedelta) -> str:
    """Подписывает токен.

    :param token_type: Тип токен, 'access' или 'refresh'.
    :param payload: Дополнительные данные, которые нужно закодировать в токен.
    :param expires_in: Время через которое истекает токен.
    :return Подписанный токен заданного типа.
    """
    now = current_datetime()
    expires_at = now + expires_in
    payload.update({
        "exp": expires_at.timestamp(),
        "iat": now.timestamp(),
        "token_type": token_type,
        "jti": str(uuid4())
    })
    return jwt.encode(
        payload=payload,
        key=settings.jwt.secret_key,
        algorithm=settings.jwt.algorithm
    )


def decode_token(token: str) -> dict[str, Any]:
    """Декодирует токен.

    :param token: Токен, который нужно декодировать.
    :return: Словарь с информацией из токена.
    :exception InvalidTokenError: Токен не был подписан этим сервисом.
    """
    try:
        return jwt.decode(
            token,
            key=settings.jwt.secret_key,
            algorithms=[settings.jwt.algorithm],
            options={"verify_aud": False}
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token expired!") from None
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid token!") from None
