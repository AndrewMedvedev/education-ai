from enum import StrEnum, auto


class AssignmentType(StrEnum):
    PRACTICE = auto()
    QUIZ = auto()


class AssignmentSource(StrEnum):
    TEACHER = auto()
    AI = auto()


class AssignmentStatus(StrEnum):
    DRAFT = auto()
    PUBLISHED = auto()
    ARCHIVED = auto()


class AttemptStatus(StrEnum):
    IN_PROGRESS = auto()
    SUBMITTED = auto()
    COMPLETED = auto()
    FAILED = auto()


class QuestionType(StrEnum):
    SINGLE_CHOICE = auto()
    MULTIPLE_CHOICE = auto()
    TEXT = auto()


class ContentType(StrEnum):
    """Тип контента внутри блока."""

    TEXT = auto()  # Текстовый контент / лекция
    IMAGE = auto()  # Изображение
    PROGRAM_CODE = auto()  # Пример кода
    MERMAID = auto()  # Mermaid диаграмма
    QUIZ = auto()  # Вопросы для самопроверки
    MATH_FORMULA = auto()  # Математическая, физическая, логическая формула
    CHEMICAL_FORMULA = auto()  # Химическая формула
    MUSICAL_NOTATION = auto()  # Нотная запись


class ExtendedContentType(StrEnum):
    TEXT = auto()  # Текстовый контент / лекция
    VIDEO = auto()  # Видео блок
    IMAGE = auto()  # Изображение
    PROGRAM_CODE = auto()  # Пример кода
    MERMAID = auto()  # Mermaid диаграмма
    QUIZ = auto()  # Вопросы для самопроверки
    MATH_FORMULA = auto()  # Математическая, физическая, логическая формула
    CHEMICAL_FORMULA = auto()  # Химическая формула
    MUSICAL_NOTATION = auto()  # Нотная запись


class PracticeStatus(StrEnum):
    NOT_STARTED = auto()
    FAILED = auto()
    COMPLETED = auto()


class CourseStatus(StrEnum):
    """Статусы жизненного цикла курса."""

    IN_GENERATION = auto()
    DRAFT = auto()
    INVITE_ONLY = auto()
    PUBLISHED = auto()
    ARCHIVED = auto()


class DifficultyLevel(StrEnum):
    """Уровни сложности для образовательной платформы."""

    BEGINNER = auto()  # Начальный
    INTERMEDIATE = auto()  # Средний
    ADVANCED = auto()  # Продвинутый
    EXPERT = auto()  # Экспертный


class DocumentNodeType(StrEnum):
    TOC = auto()
    HEADING = auto()
    TEXT = auto()
