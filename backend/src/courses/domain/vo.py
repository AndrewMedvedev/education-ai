from enum import StrEnum, auto


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


class GenerationStatus(StrEnum):
    """Статусы фоновой генерации курса."""

    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()


class DocumentNodeType(StrEnum):
    TOC = auto()
    HEADING = auto()
    TEXT = auto()


class TestType(StrEnum):
    """Тип тестирования"""

    MULTIPLE_CHOICE = auto()
    DETAILED_ANSWER = auto()


class AssignmentType(StrEnum):
    """Тип практического задания."""

    FILE_UPLOAD = "file_upload"  # Загрузка файла
    GITHUB = "github"  # Работа с GitHub-репозиторием
