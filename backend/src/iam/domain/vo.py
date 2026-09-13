from typing import ClassVar

import re
from dataclasses import dataclass, field
from enum import StrEnum, auto

from email_validator import EmailNotValidError, validate_email

from src.shared.domain.vo import ValueObject


class PermissionScope(StrEnum):
    """
    Уровни доступа:
     - `global` - админ платформы.
     - `organization` - в рамках компании.
     - `project` - в рамках проекта.
     - `own` - только своё.
     - `object` - уровень объекта.
    """

    GLOBAL = auto()
    ORGANIZATION = auto()
    COURSE = auto()
    OWN = auto()
    OBJECT = auto()


@dataclass(frozen=True, slots=True)
class PermissionGrant:
    """Назначенное право."""

    permission: str
    scope: PermissionScope


@dataclass(frozen=True, slots=True)
class FullName(ValueObject):
    """
    ФИО - доменный примитив для валидации российских имён
    """

    MIN_PARTS: ClassVar[int] = 2
    MAX_LENGTH: ClassVar[int] = 155

    value: str = field(compare=True, hash=True)

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("Full name cannot be empty")

        if len(self.value) >= self.MAX_LENGTH:
            raise ValueError("Full name cannot be longer than 155 characters")

        parts = [part.strip() for part in self.value.split() if part.strip()]
        if len(parts) < self.MIN_PARTS:
            raise ValueError("Must have at least first and last name")

        pattern = re.compile(r"^[A-Za-zА-Яа-яЁё\s\-'’]+$")
        if not all(pattern.match(p) for p in parts):
            raise ValueError(f"Invalid characters in full name: {self.value!r}")

        normalized_parts = [p.title() for p in parts]
        normalized = " ".join(normalized_parts)

        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"FullName({self.value!r})"

    def __eq__(self, other) -> bool:
        if isinstance(other, FullName):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other.strip().title()
        return NotImplemented

    @property
    def _parts(self) -> list[str]:
        return self.value.split()

    @property
    def last_name(self) -> str:
        """Фамилия (вторая часть)"""

        return self._parts[-1]

    @property
    def first_name(self) -> str:
        """Имя (первая часть)"""

        return self._parts[0]

    @property
    def middle_name(self) -> str | None:
        """Отчество"""

        if len(self._parts) > self.MIN_PARTS:
            return " ".join(self._parts[1:-1])
        return None


@dataclass(frozen=True, slots=True)
class Username(ValueObject):
    """
    Доменный примитив — имя пользователя (логин).

    Характеристики:
    - 3–30 символов
    - разрешены: a-z, 0-9, _,., —
    - не начинается и не заканчивается на _,., —
    - не содержит два подряд специальных символа (_,., —)
    - хранится и сравнивается в нижнем регистре
    """

    MIN_LENGTH: ClassVar[int] = 3
    MAX_LENGTH: ClassVar[int] = 30

    # Что проверяет это регулярное выражение:
    # - начинается и заканчивается буквой или цифрой
    # - внутри: буквы, цифры, и не более одного спецсимвола подряд
    PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^[a-zа-яё0-9](?:(?![._-]{2})[a-zа-яё0-9._-])*[a-zа-яё0-9]$", re.IGNORECASE
    )

    value: str = field(compare=True, hash=True, repr=False)

    def __post_init__(self) -> None:

        cleaned = self.value.strip().lower()

        if not cleaned:
            raise ValueError("Username cannot be empty")

        if len(cleaned) < self.MIN_LENGTH:
            raise ValueError(f"Username too short (minimum {self.MIN_LENGTH} characters)")

        if len(cleaned) > self.MAX_LENGTH:
            raise ValueError(f"Username too long (max {self.MAX_LENGTH} characters)")

        if not self.PATTERN.match(cleaned):
            raise ValueError(
                "Username can only contains letters, numbers, periods, hyphens and underscores. "
                "Cannot planned_start or planned_end with a special character, "
                "cannot contain two special characters in a row."
            )

        if cleaned.isdigit():
            raise ValueError("Username cannot contains only digits")

        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Username({self.value!r})"

    def __eq__(self, other) -> bool:
        if isinstance(other, Username):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other.strip().lower()
        return NotImplemented


@dataclass(frozen=True, slots=True)
class Email:
    value: str = field(compare=True, hash=True)

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("Email cannot be empty")

        try:
            validation = validate_email(self.value, check_deliverability=False)
            normalized = validation.normalized
        except EmailNotValidError as e:
            raise ValueError("Invalid email address") from e

        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Email({self.value!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Email):
            return self.value == other.value

        if isinstance(other, str):
            try:
                validation = validate_email(self.value, check_deliverability=False)
            except EmailNotValidError:
                return False
            else:
                return self.value == validation.normalized

        return NotImplemented

    @property
    def domain(self) -> str:
        return self.value.split("@")[-1]


@dataclass(frozen=True, slots=True)
class SecretHash(ValueObject):
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("Secret hash cannot be empty")

    def __repr__(self) -> str:
        return "SecretHash(******)"

    def __str__(self) -> str:
        return "******"

    def get_hashed_value(self) -> str:
        return self.value
