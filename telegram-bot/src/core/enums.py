from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    TEACHER = "teachers"
    STUDENT = "student"


class ContentType(StrEnum):
    TEXT = "text"
    VIDEO = "video"
    CODE = "code"
    QUIZ = "quiz"


class ExerciseType(StrEnum):
    """Тип практического задания"""

    TEST = "test"
    FILE_UPLOAD = "file_upload"
    GITHUB = "github"


class AssessmentType(StrEnum):
    TEST = "test"
    PROJECT = "project"
    ESSAY = "essay"
    PRESENTATION = "presentation"
