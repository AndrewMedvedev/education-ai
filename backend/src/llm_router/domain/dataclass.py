from dataclasses import dataclass

from src.shared.domain.entities import Entity


@dataclass(kw_only=True)
class AIModel(Entity):
    """Хранит структурированные данные `AIModel`, чтобы передавать их между слоями без словарей."""

    name: str
    description: str
    context: int
