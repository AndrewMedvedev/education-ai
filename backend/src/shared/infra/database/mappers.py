import abc

from src.core.database import Base
from src.shared.domain.entities import Entity


class ModelMapper[EntityT: Entity, ModelT: Base](abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def from_model(model: ModelT) -> EntityT:
        """Преобразование ORM модели в доменную сущность"""

    @staticmethod
    @abc.abstractmethod
    def to_model(entity: EntityT) -> ModelT:
        """Преобразование доменной сущности в ORM модель"""
