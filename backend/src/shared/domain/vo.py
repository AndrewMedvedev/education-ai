import abc
from dataclasses import dataclass, field
from enum import StrEnum, auto

from email_validator import EmailNotValidError, validate_email


@dataclass(frozen=True, slots=True)
class ValueObject(abc.ABC):
    """
    Базовый класс для объекта значения, идентичность определяется комбинацией полей
    """

    def __eq__(self, other) -> bool:
        if isinstance(other, ValueObject):
            return self.__dict__ == other.__dict__
        return False

    def __hash__(self) -> int:
        return hash(tuple(self.__dict__.values()))

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"({', '.join(f'{k}={v!r}' for k, v in self.__dict__.items())})"
        )


class Priority(StrEnum):
    """
    Приоритет выполнения рабочей единицы (задача, тикет, ...).
    """

    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass(frozen=True, slots=True)
class Tag(ValueObject):
    """
    Тег - метка (ключевое слово), которые можно присвоить сущности
    для дополнительной, неструктурированной классификации.
    """

    name: str
    color: str = field(default="#3498db")

    def __str__(self) -> str:
        return self.name


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
