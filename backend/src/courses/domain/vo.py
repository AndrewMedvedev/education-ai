# pyright: reportAssignmentType=false
from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
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


class DocumentNodeType(StrEnum):
    TOC = auto()
    HEADING = auto()
    TEXT = auto()


class MemberRole(StrEnum):
    TEACHER = auto()  # Преподаватель
    MODERATOR = auto()  # Модератор
    STUDENT = auto()  # Студент

    @property
    def level(self) -> int:
        return {
            MemberRole.STUDENT: 1,
            MemberRole.MODERATOR: 2,
            MemberRole.TEACHER: 3,
        }[self]

    def can_assign(self, role: MemberRole) -> bool:
        return self.level >= role.level


class TestType(StrEnum):
    """Тип тестирования"""

    MULTIPLE_CHOICE = auto()
    DETAILED_ANSWER = auto()


class AssignmentType(StrEnum):
    """Тип практического задания."""

    FILE_UPLOAD = "file_upload"  # Загрузка файла
    GITHUB = "github"  # Работа с GitHub-репозиторием


@dataclass(kw_only=True, slots=True)
class ContentBlock(ABC):
    """Базовый блок контента.

    Attributes:
        content_type: Тип содержимого блока (текст, видео, код и т.д.).
        ai_generated: Флаг, указывающий, сгенерирован ли контент искусственным интеллектом.
    """

    content_type: ContentType
    ai_generated: bool = True


@dataclass(kw_only=True, slots=True)
class TextBlock(ContentBlock):
    """Блок с текстовым теоретическим материалом.

    Attributes:
        content_type: Тип контента (всегда TEXT).
        ai_generated: Флаг AI-генерации.
        md_content: Текст лекции в формате Markdown.
    """

    content_type: ContentType = ContentType.TEXT
    md_content: str


@dataclass(kw_only=True, slots=True)
class VideoBlock(ContentBlock):
    """Блок с видео материалом.

    Attributes:
        content_type: Тип контента (всегда VIDEO).
        ai_generated: Флаг AI-генерации.
        url: ссылка на Видео.
    """

    content_type: ContentType = ExtendedContentType.VIDEO
    url: str
    description: str


@dataclass(kw_only=True, slots=True)
class ImageBlock(ContentBlock):
    """Блок с изображением.

    Attributes:
        content_type: Тип контента (всегда IMAGE).
        ai_generated: Флаг AI-генерации.
        image_id: id изображения.
    """

    content_type: ContentType = ContentType.IMAGE
    image_id: str


@dataclass(kw_only=True, slots=True)
class CodeBlock(ContentBlock):
    """Блок с примером программного кода.

    Attributes:
        content_type: Тип контента (всегда PROGRAM_CODE).
        ai_generated: Флаг AI-генерации.
        language: Язык программирования (python, javascript и т.д.).
        code: Исходный код примера.
        explanation: Пояснение к коду.
    """

    content_type: ContentType = ContentType.PROGRAM_CODE
    language: str
    code: str
    explanation: str


@dataclass(kw_only=True, slots=True)
class MermaidBlock(ContentBlock):
    """Блок с Mermaid диаграммой.

    Attributes:
        content_type: Тип контента (всегда MERMAID).
        ai_generated: Флаг AI-генерации.
        title: Заголовок диаграммы.
        md_content: Код диаграммы в синтаксисе Mermaid.
        explanation: Текстовое описание диаграммы.
    """

    content_type: ContentType = ContentType.MERMAID
    title: str
    md_content: str
    explanation: str


@dataclass(kw_only=True, slots=True)
class Question:
    """Блок с Вопросом (базовый для разных типов вопросов).

    Attributes:
        question: Вопрос в формате строки.
        answer: Ответ на вопрос в формате строки.
    """

    question: str
    answer: str


@dataclass(kw_only=True, slots=True)
class QuizBlock(ContentBlock):
    """Блок с вопросами и ответами.

    Attributes:
        content_type: Тип контента (всегда QUIZ).
        ai_generated: Флаг AI-генерации.
        questions: Список вопросов и ответов.
    """

    content_type: ContentType = ContentType.QUIZ
    questions: list[Question] = field(default_factory=list)


@dataclass(kw_only=True)
class FormulaBlock:
    """Блок с формулой (базовый для разных типов формул).

    Attributes:
        formula: Строковое представление формулы (LaTeX‑подобный синтаксис).
        explanation: Пояснение к формуле.
    """

    formula: str
    explanation: str


@dataclass(kw_only=True, slots=True)
class MathBlock(FormulaBlock, ContentBlock):
    """Блок с математической формулой.

    Attributes:
        content_type: Тип контента (всегда MATH_FORMULA).
        ai_generated: Флаг AI-генерации.
        formula: Математическое выражение.
        explanation: Пояснение.
    """

    content_type: ContentType = ContentType.MATH_FORMULA


@dataclass(kw_only=True, slots=True)
class ChemicalBlock(FormulaBlock, ContentBlock):
    """Блок с химической формулой.

    Attributes:
        content_type: Тип контента (всегда CHEMICAL_FORMULA).
        ai_generated: Флаг AI-генерации.
        formula: Химическая формула.
        explanation: Пояснение.
    """

    content_type: ContentType = ContentType.CHEMICAL_FORMULA


@dataclass(kw_only=True, slots=True)
class MusicalBlock(FormulaBlock, ContentBlock):
    """Блок с нотной записью.

    Attributes:
        content_type: Тип контента (всегда MUSICAL_NOTATION).
        ai_generated: Флаг AI-генерации.
        formula: Нотная запись в текстовом формате (например, ABC-нотация).
        explanation: Пояснение.
    """

    content_type: ContentType = ContentType.MUSICAL_NOTATION


AnyContentBlock = (
    TextBlock
    | VideoBlock
    | ImageBlock
    | CodeBlock
    | QuizBlock
    | MermaidBlock
    | MathBlock
    | ChemicalBlock
    | MusicalBlock
)


@dataclass(kw_only=True, slots=True)
class Assignment(ABC):
    """Базовая модель задания.

    Attributes:
        assignment_type: Тип задания (загрузка файла или GitHub).
        title: Заголовок задания.
        description: Описание задания.
        evaluation_criteria: Критерии оценки (список строк).
        passing_score: Минимальный балл для зачёта (от 0 до 100, по умолчанию 61).
    """

    assignment_type: AssignmentType
    title: str
    description: str
    evaluation_criteria: list[str]
    passing_score: int = 61


@dataclass(kw_only=True, slots=True)
class FileUploadAssignment(Assignment):
    """Задание с загрузкой файла.

    Attributes:
        assignment_type: Тип задания (всегда FILE_UPLOAD).
        title: Заголовок.
        description: Описание.
        evaluation_criteria: Критерии оценки.
        passing_score: Проходной балл.
        allowed_extensions: Список разрешённых расширений файлов (по умолчанию "*" – любые).
        submission_instructions: Инструкция по отправке работы.
    """

    assignment_type: AssignmentType = AssignmentType.FILE_UPLOAD
    allowed_extensions: list[str] = field(default_factory=lambda: ["*"])
    submission_instructions: str


@dataclass(kw_only=True, slots=True)
class GitHubAssignment(Assignment):
    """Задание с GitHub-репозиторием.

    Attributes:
        assignment_type: Тип задания (всегда GITHUB).
        title: Заголовок.
        description: Описание.
        evaluation_criteria: Критерии оценки.
        passing_score: Проходной балл.
        repository_rules: Правила работы с репозиторием (структура, коммиты, оформление).
        required_branch: Ветка, которую должен использовать студент (по умолчанию "main").
    """

    assignment_type: AssignmentType = AssignmentType.GITHUB
    repository_rules: str
    required_branch: str = "main"


AnyAssignment = FileUploadAssignment | GitHubAssignment
