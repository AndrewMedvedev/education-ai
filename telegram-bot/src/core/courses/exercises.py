from typing import TypeVar

from abc import ABC
from enum import StrEnum

from pydantic import BaseModel, Field, NonNegativeInt, PositiveInt


class ExerciseType(StrEnum):
    """Тип практического задания"""

    TEST = "test"
    FILE_UPLOAD = "file_upload"
    GITHUB = "github"


class Exercise(ABC, BaseModel):
    """Базовая модель для создания упражнений/заданий"""

    exercise_type: ExerciseType
    version: NonNegativeInt = Field(
        default=0,
        description="""
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


AnyExercise = TypeVar("AnyExercise", bound=Exercise)


class TestQuestion(BaseModel):
    """Вопрос внутри тестирования"""

    text: str = Field(..., description="Формулировка вопроса")
    options: list[str] = Field(
        default_factory=list, description="Варианты ответов (порядок имеет значение)"
    )
    correct_answers: list[int] = Field(
        default_factory=list,
        description="Индексы правильных ответов начиная с 0",
        examples=[{0, 3, 4}, {1}, {2, 5}]
    )
    points: PositiveInt = Field(..., description="Количество баллов за правильный ответ")


class TestExercise(Exercise):
    """Задание в виде теста"""

    exercise_type: ExerciseType = ExerciseType.TEST

    questions: list[TestQuestion] = Field(
        default_factory=list,
        min_length=1,
        description="список тестовых вопросов"
    )


class FileUploadExercise(Exercise):
    """Задание с загрузкой файла"""

    exercise_type: ExerciseType = ExerciseType.FILE_UPLOAD

    task: str = Field(..., description="Текст задания, который увидит студент")
    allowed_extensions: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Разрешённые расширения файлов",
        examples=[[".pdf", ".docx"], [".pptx", ".pdf"], [".py"]]
    )
    submission_instructions: str = Field(
        ..., description="Дополнительные инструкции по оформлению работы"
    )


class GitHubExercise(Exercise):
    """Задание выполняющиеся в GitHub репозитории"""

    repository_task: str = Field(
        ..., description="Задание, которое нужно выполнить в репозитории"
    )
    repository_rules: str = Field(..., description="Правила оформления репозитория")
    required_branch: str = Field(default="main", description="Требуемая ветка для проверки")
