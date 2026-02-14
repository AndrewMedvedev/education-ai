from enum import StrEnum

from pydantic import BaseModel, PositiveInt


class TeacherContext(BaseModel):
    """Контекст преподавателя для генерации образовательного курса"""

    user_id: PositiveInt
    comment: str
    tenant_id: str


class GeneratedContentType(StrEnum):
    """Генерируемый контент"""

    TEXT = "text"  # Текстовый контент / лекция
    PROGRAM_CODE = "program_code"  # Пример кода
    MERMAID = "mermaid"  # Mermaid диаграмма
    QUIZ = "quiz"  # Вопросы для самопроверки
