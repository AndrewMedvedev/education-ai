from typing import Any

import asyncio
import logging
import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import UUID, uuid4

import jwt
import zxcvbn_rs_py
from passlib.context import CryptContext

from src.core.settings import jwt_config, settings
from src.iam.application.dtos import IdentityType
from src.iam.consts import CLIENT_ID_BYTES_LENGTH, CLIENT_SECRET_BYTES_LENGTH
from src.iam.domain.exceptions import UnauthorizedError, WeakPasswordError
from src.iam.domain.vo import Email
from src.shared.utils.time import current_datetime

MEMORY_COST = 100
TIME_COST = 2
PARALLELISM = 2
SALT_SIZE = 16
ROUNDS = 14

logger = logging.getLogger(__name__)

pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    default="argon2",
    argon2__memory_cost=MEMORY_COST,
    argon2__time_cost=TIME_COST,
    argon2__parallelism=PARALLELISM,
    argon2__salt_size=SALT_SIZE,
    bcrypt__rounds=ROUNDS,
    deprecated="auto",
)

MAX_WORKERS = max(1, (os.cpu_count() or 2) // 2)

# В `lifespan` вызвать `crypto_executor.shutdown(wait=True)`
crypto_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="crypto_worker")


async def hash_password_async(password: str) -> str:
    """Асинхронное хэширует пароль в отдельном потоке."""

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(crypto_executor, hash_password, password)


async def verify_password_async(plain_password: str, password_hash: str) -> bool:
    """Асинхронно сверяет хеш пароля в отдельном потоке."""

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        crypto_executor, verify_password, plain_password, password_hash
    )


async def validate_password_strength_async(
    password: str,
    email: Email | None = None,
    *,
    min_score: int = 3,
) -> None:
    """Асинхронная обёртка для проверки надёжности пароля."""

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        crypto_executor,
        validate_password_strength,
        password,
        email,
        min_score,
    )


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_authentication_token(user_id: UUID) -> str:
    """Выпускает очень короткоживущий токен для аутентификации."""

    now = current_datetime()
    expires_at = now + timedelta(minutes=jwt_config.authentication_token_expires_in_minutes)

    payload = {
        "sub": str(user_id),
        "typ": "authentication",
        "jti": str(uuid4()),
        "exp": expires_at.timestamp(),
        "iat": now.timestamp(),
    }

    return jwt.encode(payload=payload, key=settings.secret_key, algorithm=jwt_config.algorithm)


def create_access_token(
    *,
    identity_id: UUID,
    identity_type: IdentityType,
    organization_id: UUID,
    roles: set[str],
    permissions: set[str],
    email: Email | None = None,
    membership_id: UUID | None = None,
) -> str:

    now = current_datetime()
    expires_at = now + timedelta(minutes=jwt_config.access_token_expires_in_minutes)

    payload = {
        # Базовые поля
        "sub": str(identity_id),
        "exp": expires_at.timestamp(),
        "iat": now.timestamp(),
        "typ": "access",
        "jti": str(uuid4()),
        # Кастомные поля
        "idt": identity_type.value,
        "org_id": str(organization_id),
        "roles": list(roles),
        "perms": list(permissions),
    }

    # Специфичные для пользователя поля
    if email is not None:
        payload["email"] = email.value

    if membership_id is not None:
        payload["mid"] = str(membership_id)

    return jwt.encode(payload=payload, key=settings.secret_key, algorithm=jwt_config.algorithm)


def create_refresh_token(user_id: UUID, membership_id: UUID) -> str:
    """Выпускает долгоживущий токен для получения новой пары access + refresh."""

    now = current_datetime()
    expires_at = now + timedelta(days=jwt_config.refresh_token_expires_in_days)

    payload = {
        # Базовые поля
        "sub": str(user_id),
        "exp": expires_at.timestamp(),
        "iat": now.timestamp(),
        "typ": "refresh",
        "jti": str(uuid4()),
        # Кастомные поля
        "mid": str(membership_id),
    }

    return jwt.encode(payload=payload, key=settings.secret_key, algorithm=jwt_config.algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Декодирует JWT и проверяет его подпись и срок действия."""

    try:
        return jwt.decode(
            token,
            key=settings.secret_key,
            algorithms=[jwt_config.algorithm],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token signature expired!") from None
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid token!") from None


def validate_password_strength(
    password: str,
    email: Email | None = None,
    *,
    min_score: int = 3,
) -> None:
    """
    Проверяет надежность пароля с помощью Rust-реализации zxcvbn.
    При слабом пароле выбрасывает WeakPasswordError
    """

    sanitized_inputs = [email.value] if email is not None else []

    result = zxcvbn_rs_py.zxcvbn(password, user_inputs=sanitized_inputs)

    if result < min_score:
        warning = result.feedback.warning.value if result.feedback.warning else None
        suggestions = (
            [suggestion.value for suggestion in result.feedback.suggestions]
            if result.feedback.suggestions
            else []
        )

        raise WeakPasswordError("Password is too weak.", suggestions=suggestions, warning=warning)


def generate_client_id() -> str:
    """Генерирует публичный идентификатор сервисного аккаунта."""

    return secrets.token_urlsafe(CLIENT_ID_BYTES_LENGTH)


def generate_client_secret() -> str:
    """Генерирует криптографически стойкий client secret."""

    return secrets.token_urlsafe(CLIENT_SECRET_BYTES_LENGTH)
