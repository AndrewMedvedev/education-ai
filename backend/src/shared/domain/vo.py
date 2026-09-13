import abc
from dataclasses import dataclass, field
from enum import StrEnum, auto


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
