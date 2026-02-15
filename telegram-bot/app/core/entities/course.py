from abc import ABC
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt

from ..commons import current_datetime


class ContentType(StrEnum):
    """Тип контента внутри блока"""

    TEXT = "text"  # Текстовый контент / лекция
    VIDEO = "video"  # Видео из стороннего источника
    PROGRAM_CODE = "program_code"  # Пример кода
    MERMAID = "mermaid"  # Mermaid диаграмма
    QUIZ = "quiz"  # Вопросы для самопроверки
    LINK = "link"  # Внешняя ссылка на источник


class ContentBlock(ABC, BaseModel):
    """Универсальные блоки с контентом"""

    model_config = ConfigDict(from_attributes=True)

    content_type: ContentType
    ai_generated: bool = Field(default=True)


class TextBlock(ContentBlock):
    content_type: ContentType = ContentType.TEXT

    md_content: str = Field(..., description="Markdown текст теоретического материала")


class VideoBlock(ContentBlock):
    """Блок с видео контентом"""

    content_type: ContentType = ContentType.VIDEO

    url: str = Field(..., description="Ссылка на видео")
    platform: str = Field(
        ..., description="Платформа с которой взято видео", examples=["YouTube", "RuTube"]
    )
    title: str = Field(..., description="Название видео")
    duration_seconds: PositiveInt = Field(..., description="Длительность в секундах")
    key_moments: list[tuple[str, str]] = Field(
        default_factory=list,
        description="Тайм-коды ключевых моментов",
        examples=[[("1:05", "Вступление"), ("5:23", "Начало лекции")]]
    )
    discussion_questions: list[str] = Field(
        default_factory=list, description="Вопросы для обсуждения"
    )


class CodeBlock(ContentBlock):
    """Пример кода"""

    content_type: ContentType = ContentType.PROGRAM_CODE

    language: str = Field(..., description="Язык программирования")
    code: str = Field(..., description="Программный код")
    explanation: str = Field(..., description="Пояснения к коду")


class MermaidBlock(ContentBlock):
    """Блок с mermaid диаграммой"""

    content_type: ContentType = ContentType.MERMAID

    title: str = Field(..., description="Название диаграммы")
    mermaid_code: str = Field(..., description="Mermaid код в Markdown формате")
    explanation: str = Field(..., description="Пояснение диаграммы")


class QuizBlock(ContentBlock):
    """Блок с вопросами для самопроверки"""

    content_type: ContentType = ContentType.QUIZ

    questions: list[tuple[str, str]] = Field(
        default_factory=list,
        description="Список вопросов для самопроверки с ответами",
        examples=[
            [
                ("Здесь должен быть первый вопрос", "Ответ на первый вопрос"),
                ("Здесь должен быть второй вопрос", "Ответ на второй вопрос"),
            ]
        ],
    )


class LinkBlock(ContentBlock):
    """Блок для прикрепления внешней ссылки, например на Яндекс диск, Google drive, ..."""

    content_type: ContentType = ContentType.LINK

    title: str = Field(..., description="Название прикреплённого материала")
    url: str = Field(..., description="Ссылка на внешний источник")
    ai_generated: bool = Field(default=False)


AnyContentBlock = TextBlock | VideoBlock | CodeBlock | QuizBlock | MermaidBlock | LinkBlock


class AssignmentType(StrEnum):
    """Тип практического задания"""

    TEST = "test"
    FILE_UPLOAD = "file_upload"
    GITHUB = "github"


class Assignment(ABC, BaseModel):
    """Базовая модель для создания упражнений/заданий"""

    model_config = ConfigDict(from_attributes=True)

    assignment_type: AssignmentType
    version: NonNegativeInt = Field(
        default=0,
        description="""\
        Версия задания. 0 - оригинальная версия преподавателя.
        >0 - сгенерированные варианты для предотвращения списывания"""
    )
    title: str = Field(..., description="Название")
    max_score: PositiveInt = Field(
        ..., description="Максимальное количество баллов, которое можно получить за выполнение"
    )
    passing_score: PositiveInt = Field(
        ..., description="Минимальное количество баллов, которое нужно набрать чтобы сдать задание"
    )


class TestQuestion(BaseModel):
    """Вопрос внутри тестирования"""

    text: str = Field(..., description="Формулировка задания/вопроса")
    options: list[str] = Field(
        default_factory=list,
        min_length=2,
        max_length=7,
        description="Варианты ответов (порядок имеет значение)"
    )
    correct_answers: list[int] = Field(
        default_factory=list,
        min_length=1,
        max_length=7,
        description="Индексы правильных ответов начиная с 0",
        examples=[[0, 3, 4], [1], [2, 5]]
    )
    points: PositiveInt = Field(..., description="Количество баллов за правильный ответ")


class TestAssignment(Assignment):
    """Задание в виде теста"""

    assignment_type: AssignmentType = AssignmentType.TEST

    questions: list[TestQuestion] = Field(
        default_factory=list,
        min_length=5,
        description="Список тестовых вопросов"
    )


class FileUploadAssignment(Assignment):
    """Задание с загрузкой файла"""

    assignment_type: AssignmentType = AssignmentType.FILE_UPLOAD

    task: str = Field(..., description="Подробно сформулированное задание")
    allowed_extensions: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Разрешённые расширения файлов",
        examples=[[".pdf", ".docx"], [".pptx", ".pdf"], [".py"]]
    )
    submission_instructions: str = Field(
        ..., description="Дополнительные инструкции по оформлению работы"
    )


class GitHubAssignment(Assignment):
    """Задание выполняющиеся в GitHub репозитории"""

    assignment_type: AssignmentType = AssignmentType.GITHUB

    repository_task: str = Field(
        ..., description="ТЗ для выполнения задания, включает требования, ожидаемый результат, ..."
    )
    repository_rules: str = Field(..., description="Правила оформления репозитория")
    required_branch: str = Field(default="main", description="Требуемая ветка для проверки")


AnyAssignment = TestAssignment | FileUploadAssignment | GitHubAssignment


class Module(BaseModel):
    """Модуль - часть образовательного курса"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., description="Название модуля")
    description: str = Field(..., description="Описание модуля для студента")
    learning_objectives: list[str] = Field(
        default_factory=list, description="Цели обучения модуля"
    )
    order: NonNegativeInt = Field(
        ..., description="Порядковый номер модуля внутри курса (начинается с 0)"
    )
    content_blocks: list[AnyContentBlock] = Field(
        default_factory=list,
        min_length=1,
        description="Контент блоки с материалом для изучения"
    )
    assignment: AnyAssignment | None = Field(
        default=None, description="Задание для закрепления материала"
    )

    def append_content_block(self, content_block: AnyContentBlock) -> None:
        self.content_blocks.append(content_block)

    def add_assignment(self, assignment: AnyAssignment) -> None:
        self.assignment = assignment


class FinalAssessment(BaseModel):
    """Финальный ассессмент в конце курса"""

    version: NonNegativeInt = Field(
        default=0,
        description="""
            Версия задания. 0 - оригинальная версия преподавателя.
            >0 - сгенерированные варианты для предотвращения списывания""",
    )
    task: str = Field(
        ...,
        description="""
        Текст задания, который увидит студент
        (может быть описание финального проекта, презентации, задачи для решения или иное)
        """
    )
    evaluation_criteria: list[str] = Field(..., description="Критерии для оценки")


class CourseStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Course(BaseModel):
    """Модель образовательного курса"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=current_datetime)
    creator_id: PositiveInt
    status: CourseStatus = Field(default=CourseStatus.IN_PROGRESS)
    image_url: str | None = None
    title: str
    description: str
    learning_objectives: list[str] = Field(default_factory=list, min_length=2)
    modules: list[Module] = Field(default_factory=list, min_length=1)
    final_assessment: FinalAssessment | None = None

    def append_module(self, module: Module) -> None:
        self.modules.append(module)

    def add_final_assessment(self, final_assessment: FinalAssessment) -> None:
        self.final_assessment = final_assessment
