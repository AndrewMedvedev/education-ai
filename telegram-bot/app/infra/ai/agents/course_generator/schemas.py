from typing import Literal

from enum import StrEnum

from pydantic import BaseModel, Field, NonNegativeFloat, PositiveInt


class TeacherContext(BaseModel):
    """Контекст преподавателя для генерации образовательного курса"""

    user_id: PositiveInt
    comment: str
    tenant_id: str


class GeneratedContentType(StrEnum):
    """Генерируемые типы контента"""

    TEXT = "text"  # Текстовый контент / лекция
    PROGRAM_CODE = "program_code"  # Пример кода
    MERMAID = "mermaid"  # Mermaid диаграмма
    QUIZ = "quiz"  # Вопросы для самопроверки


class Knowledge(BaseModel):
    """Знания полученные в ходе создания образовательного курса"""

    tenant_id: str = Field(..., description="ID выделенного тенанта в поисковом индексе")
    category: Literal["materials", "web_research", "theory"] = Field(
        default="web_research",
        description="""\
        Тип знаний:
         - materials - информация полученная из материалов преподавателя
         - web_research - информация полученная в ходе изучения предметной области
         - theory - теоретический материал уже созданного курса
        """
    )
    source: str = Field(
        ...,
        description="Источник полученных знаний, например имя файла, URL адрес, название ресурса"
    )
    text: str = Field(..., description="Полезная информация, которую необходимо запомнить")
    score: NonNegativeFloat = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Насколько полезна информация, где 1 максимально релевантная информация"
    )
