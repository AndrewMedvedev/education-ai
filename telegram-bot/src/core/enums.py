from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    TEACHER = "teachers"
    STUDENT = "student"


class ContentType(StrEnum):
    TEXT = "text"
    VIDEO = "video"
    INFOGRAPHIC = "infographic"
    CODE = "code"
    QUIZ = "quiz"
    TEST = "test"


class SubmissionFormat(StrEnum):
    """Формат сдачи задания"""

    TEXT = "text"
    FILE = "file"
    CODE = "code"
    GITHUB = "github"
    URL = "url"


class AssessmentType(StrEnum):
    TEST = "test"
    PROJECT = "project"
    ESSAY = "essay"
    PRESENTATION = "presentation"
