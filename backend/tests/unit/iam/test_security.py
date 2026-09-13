from datetime import timedelta
from uuid import uuid4

import jwt
import pytest
from freezegun import freeze_time

from src.core.settings import settings
from src.iam.domain.exceptions import UnauthorizedError
from src.iam.domain.vo import UserRole
from src.iam.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    validate_token,
    verify_password,
)
from src.shared.utils.time import current_datetime, get_expiration_timestamp


class TestHashPassword:
    def test_hash_password_returns_different_string(self):  # noqa: PLR6301
        """Выполняет действие `test_hash_password_returns_different_string`, чтобы поддержать основной сценарий модуля."""
        password = "secret"
        password_hash = hash_password(password)

        assert password_hash != password
        assert isinstance(password_hash, str)

    def test_verify_password_correct(self):  # noqa: PLR6301
        """Выполняет действие `test_verify_password_correct`, чтобы поддержать основной сценарий модуля."""
        password = "secret"
        password_hash = hash_password(password)

        assert verify_password(password, password_hash) is True

    def test_verify_password_incorrect(self):  # noqa: PLR6301
        """Выполняет действие `test_verify_password_incorrect`, чтобы поддержать основной сценарий модуля."""
        password = "secret"
        password_hash = hash_password(password)

        assert verify_password("wrong", password_hash) is False


class TestValidateToken:
    def test_validate_token_correct_access_token(self):  # noqa: PLR6301
        """Выполняет действие `test_validate_token_correct_access_token`, чтобы поддержать основной сценарий модуля."""
        user_id = uuid4()
        email = "support@example.com"
        user_role = UserRole.USER

        with freeze_time("2026-03-26 10:00:00"):
            access_token = create_access_token(user_id=user_id, email=email, user_role=user_role)

            payload = validate_token(access_token)

            assert payload["sub"] == str(user_id)
            assert payload["email"] == email
            assert payload["type"] == "access"
            assert payload["role"] == user_role.value
            assert isinstance(payload["iat"], (int, float))
            assert isinstance(payload["exp"], (int, float))
            assert payload["exp"] > payload["iat"]

    def test_validate_token_correct_refresh_token(self):  # noqa: PLR6301
        """Выполняет действие `test_validate_token_correct_refresh_token`, чтобы поддержать основной сценарий модуля."""
        user_id = uuid4()

        with freeze_time("2026-03-26 10:00:00"):
            refresh_token = create_refresh_token(user_id=user_id)

            payload = validate_token(refresh_token)

            assert payload["sub"] == str(user_id)
            assert payload["type"] == "refresh"
            assert "email" not in payload
            assert "role" not in payload

            assert isinstance(payload["iat"], (int, float))
            assert isinstance(payload["exp"], (int, float))

    def test_validate_token_expired_raises_unauthorized(self):  # noqa: PLR6301
        """Выполняет действие `test_validate_token_expired_raises_unauthorized`, чтобы поддержать основной сценарий модуля."""
        user_id = uuid4()
        email = "test@example.com"
        user_role = UserRole.USER

        # Создания токена в прошлом времени (чтобы он сразу был просрочен)
        with freeze_time("2026-03-26 10:00:00"):
            access_token = create_access_token(user_id=user_id, email=email, user_role=user_role)

        # перемотка времени на час (токен уже истёк)
        with freeze_time("2026-03-26 11:00:00"):  # +1 час
            with pytest.raises(UnauthorizedError) as exc_info:
                validate_token(access_token)

            assert "Token signature expired" in str(exc_info.value)

    def test_validate_token_invalid_signature_raises_unauthorized(self):  # noqa: PLR6301
        """Выполняет действие `test_validate_token_invalid_signature_raises_unauthorized`, чтобы поддержать основной сценарий модуля."""
        invalid_token = jwt.encode(
            {"sub": "fake", "exp": 9999999999},
            key="test_secret_key_that_is_long_enough_32",  # другой ключ
            algorithm=settings.jwt.algorithm,
        )

        with pytest.raises(UnauthorizedError) as exc_info:
            validate_token(invalid_token)

        assert "Invalid token" in str(exc_info.value)

    def test_validate_token_malformed_token_raises_unauthorized(self):  # noqa: PLR6301
        """Выполняет действие `test_validate_token_malformed_token_raises_unauthorized`, чтобы поддержать основной сценарий модуля."""
        malformed_tokens = [
            "not.a.real.token",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalidpayload.signature",
            "",
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        ]

        for token in malformed_tokens:
            with pytest.raises(UnauthorizedError):
                validate_token(token)


class TestCreateAccessToken:
    def test_create_and_validate_access_token(self):  # noqa: PLR6301
        """Выполняет действие `test_create_and_validate_access_token`, чтобы поддержать основной сценарий модуля."""
        user_id = uuid4()
        email = "support@example.com"
        user_role = UserRole.USER

        with freeze_time("2026-03-26 10:00:00"):
            expected_iat = current_datetime().timestamp()
            expected_exp = get_expiration_timestamp(
                expires_in=timedelta(minutes=settings.jwt.access_token_expires_in_minutes)
            )

            access_token = create_access_token(user_id=user_id, email=email, user_role=user_role)
            payload = validate_token(access_token)

            assert payload["sub"] == f"{user_id}"
            assert payload["email"] == email
            assert payload["type"] == "access"

            assert payload["iat"] == expected_iat
            assert payload["exp"] == expected_exp

    def test_create_and_validate_access_token_with_counterparty(self):  # noqa: PLR6301
        """Выполняет действие `test_create_and_validate_access_token_with_counterparty`, чтобы поддержать основной сценарий модуля."""
        user_id = uuid4()
        email = "support@example.com"
        user_role = UserRole.USER

        with freeze_time("2026-03-26 10:00:00"):
            expected_iat = current_datetime().timestamp()
            expected_exp = get_expiration_timestamp(
                expires_in=timedelta(minutes=settings.jwt.access_token_expires_in_minutes)
            )

            access_token = create_access_token(user_id=user_id, email=email, user_role=user_role)
            payload = validate_token(access_token)

            assert payload["sub"] == f"{user_id}"
            assert payload["email"] == email
            assert payload["type"] == "access"

            assert payload["iat"] == expected_iat
            assert payload["exp"] == expected_exp


class TestCreateRefreshToken:
    def test_create_and_validate_refresh_token(self):  # noqa: PLR6301
        """Выполняет действие `test_create_and_validate_refresh_token`, чтобы поддержать основной сценарий модуля."""
        user_id = uuid4()

        with freeze_time("2026-03-26 10:00:00"):
            expected_iat = current_datetime().timestamp()
            expected_exp = get_expiration_timestamp(
                expires_in=timedelta(days=settings.jwt.refresh_token_expires_in_days)
            )

            refresh_token = create_refresh_token(user_id=user_id)
            payload = validate_token(refresh_token)

            assert payload["sub"] == f"{user_id}"
            assert payload["type"] == "refresh"
            assert "email" not in payload
            assert "role" not in payload

            assert payload["iat"] == expected_iat
            assert payload["exp"] == expected_exp
