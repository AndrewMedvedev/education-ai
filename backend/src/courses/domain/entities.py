# pyright: reportAssignmentType=false

from __future__ import annotations

from typing import Any

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from ...shared.domain.entities import AggregateRoot, Entity
from .vo import (
    AssignmentType,
    ContentType,
    CourseStatus,
    DifficultyLevel,
    DocumentNodeType,
    ExtendedContentType,
    PracticeStatus,
)


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


@dataclass(kw_only=True, slots=True)
class LessonBasicInfo:
    """Описывает доменную сущность `LessonBasicInfo` и её данные для бизнес-логики."""

    id: UUID
    title: str
    description: str
    order: int
    learning_objectives: list[str] = field(default_factory=list)
    estimated_time_minutes: int | None = None


@dataclass(kw_only=True, slots=True)
class BasicInfo:
    """Описывает доменную сущность `BasicInfo` и её данные для бизнес-логики."""

    id: UUID
    title: str
    order: int


@dataclass(kw_only=True, slots=True)
class ModuleBasicInfo:
    """Описывает доменную сущность `ModuleBasicInfo` и её данные для бизнес-логики."""

    id: UUID
    title: str
    description: str
    order: int
    learning_objectives: list[str] = field(default_factory=list)
    lessons: list[BasicInfo] = field(default_factory=list)  # [{"id": UUID, "order": int}, ...]


@dataclass(kw_only=True, slots=True)
class CourseBasicInfo:
    """Описывает доменную сущность `CourseBasicInfo` и её данные для бизнес-логики."""

    id: UUID
    title: str
    description: str
    difficulty: DifficultyLevel
    tags: list[str]
    learning_objectives: list[str] = field(default_factory=list)
    modules: list[BasicInfo] = field(default_factory=list)  # [{"id": UUID, "order": int}, ...]


@dataclass(kw_only=True, slots=True)
class Lesson(Entity):
    """Урок внутри модуля курса.

    Attributes:
        title: Название урока.
        description: Описание урока.
        order: Порядковый номер урока в модуле (начинается с 1).
        learning_objectives: Список целей урока.
        content_blocks: Дополнительные блоки контента (видео, код, тесты и т.п.).
        estimated_time_minutes: Предполагаемое время прохождения урока (в минутах).
        assignment: Практическое задание
    """

    module_id: UUID
    title: str
    description: str
    order: int
    learning_objectives: list[str] = field(default_factory=list)
    content_blocks: list[AnyContentBlock] = field(default_factory=list)
    estimated_time_minutes: int | None = None

    def append_content_block(self, content_block: AnyContentBlock) -> None:
        """Выполняет действие `append_content_block`, чтобы поддержать основной сценарий модуля."""
        self.content_blocks.append(content_block)


@dataclass(kw_only=True, slots=True)
class Module(Entity):
    """Модуль курса.

    Attributes:
        title: Название модуля.
        description: Описание модуля.
        order: Порядковый номер модуля в курсе.
        learning_objectives: Список целей модуля.
        content_blocks: Блоки контента модуля (общие для всех уроков).
        assignment: Задание модуля (может быть Assignment или сырой dict).
        lesson_basic_info: Список {"order": int, "title": str}.
        lessons: Список уроков модуля.


    """

    course_id: UUID
    title: str
    description: str
    order: int
    learning_objectives: list[str] = field(default_factory=list)
    lessons: list[Lesson] = field(default_factory=list)

    def append_lesson(self, module: Lesson) -> None:
        """Выполняет действие `append_lesson`, чтобы поддержать основной сценарий модуля."""
        self.lessons.append(module)


@dataclass(kw_only=True, slots=True)
class Course(AggregateRoot):
    """Курс.

    Attributes:
        title: Название курса.
        description: Полное описание курса.
        difficulty: Уровень сложности (beginner, intermediate, advanced).
        tags: Список тегов для поиска и категоризации.
        status: Статус курса (draft, published, archived).
        popularity: оценок популярности.
        creator_id: UUID создателя курса.
        image_url: Ссылка на обложку курса (опционально).
        learning_objectives: Список целей курса.
        final_assessment: Финальное задание (модель или dict).
        module_basic_info: Список {"order": int, "title": str}.
        modules: Список модулей курса.
    """

    title: str
    description: str
    difficulty: DifficultyLevel
    tags: list[str]
    status: CourseStatus = CourseStatus.IN_GENERATION
    popularity: int = 0
    creator_id: UUID
    image_url: str | None = None
    learning_objectives: list[str] = field(default_factory=list)
    modules: list[Module] = field(default_factory=list)
    students: list[Student] = field(default_factory=list)

    def append_module(self, module: Module) -> None:
        """Выполняет действие `append_module`, чтобы поддержать основной сценарий модуля."""
        self.modules.append(module)


@dataclass(kw_only=True, slots=True)
class LessonTheorySession(AggregateRoot):
    lesson_id: UUID
    user_id: UUID
    completed_at: datetime | None = None
    active_time_seconds: int = 0
    max_scroll_depth_percent: int = 0


@dataclass(kw_only=True, slots=True)
class Document(Entity):
    """Описывает доменную сущность `Document` и её данные для бизнес-логики."""

    owner_id: UUID
    parent_node_id: UUID | None = None
    node_type: DocumentNodeType
    title: str | None = None
    content: str | None = None


@dataclass(kw_only=True, slots=True)
class Chat(Entity):
    """Описывает доменную сущность `Chat` и её данные для бизнес-логики."""

    user_id: UUID
    course_id: UUID
    messages: list[dict] = field(default_factory=list)

    def replace_messages(self, messages: list[dict]) -> None:
        """Выполняет действие `replace_messages`, чтобы поддержать основной сценарий модуля."""
        self.messages = messages.copy()


@dataclass(kw_only=True, slots=True)
class Student(Entity):
    """Описывает доменную сущность `Student` и её данные для бизнес-логики."""

    course_id: UUID
    user_id: UUID


@dataclass(kw_only=True, slots=True)
class StudentPractice(Entity):
    """Описывает доменную сущность `StudentPractice` и её данные для бизнес-логики."""

    user_id: UUID
    course_id: UUID
    messages: list[dict] = field(default_factory=list)

    def replace_messages(self, messages: list[dict]) -> None:
        """Выполняет действие `replace_messages`, чтобы поддержать основной сценарий модуля."""
        self.messages = messages.copy()


@dataclass(kw_only=True, slots=True)
class Practice(Entity):
    """Описывает доменную сущность `Practice` и её данные для бизнес-логики."""

    user_id: UUID
    module_id: UUID
    lesson_id: UUID
    status: PracticeStatus = PracticeStatus.NOT_STARTED

    practice: list[dict[str, Any]] = field(default_factory=list)
