# pyright: reportArgumentType=false
from typing import Annotated

from fastapi import Depends

from src.shared.dependencies.database import DBSession

from ..application.services.course import CourseService
from ..application.services.document import DocumentService
from ..application.services.lesson import LessonService
from ..application.services.module import ModuleService
from ..application.services.student import StudentService
from .base import (
    CourseRepoDep,
    DocumentRepoDep,
    LessonRepoDep,
    ModuleRepoDep,
    StudentRepoDep,
)


def get_lesson_service(
    session: DBSession,
    repo: LessonRepoDep,
    module_repo: ModuleRepoDep,
) -> LessonService:
    """Получает lesson service, чтобы вызывающий код работал через единый интерфейс."""
    return LessonService(lesson_repo=repo, session=session, module_repo=module_repo)


def get_module_service(
    session: DBSession,
    repo: ModuleRepoDep,
    course_repo: CourseRepoDep,
) -> ModuleService:
    """Получает module service, чтобы вызывающий код работал через единый интерфейс."""
    return ModuleService(repo=repo, session=session, course_repo=course_repo)


def get_course_service(session: DBSession, repo: CourseRepoDep) -> CourseService:
    """Получает course service, чтобы вызывающий код работал через единый интерфейс."""
    return CourseService(repo=repo, session=session)


def get_document_service(session: DBSession, repo: DocumentRepoDep) -> DocumentService:
    """Получает document service, чтобы вызывающий код работал через единый интерфейс."""
    return DocumentService(repo=repo, session=session)


def get_student_service(
    session: DBSession,
    student_repo: StudentRepoDep,
    course_repo: CourseRepoDep,
) -> StudentService:
    """Получает student service, чтобы вызывающий код работал через единый интерфейс."""
    return StudentService(student_repo=student_repo, session=session, course_repo=course_repo)


LessonServiceDep = Annotated[LessonService, Depends(get_lesson_service)]
ModuleServiceDep = Annotated[ModuleService, Depends(get_module_service)]
CourseServiceDep = Annotated[CourseService, Depends(get_course_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
StudentServiceDep = Annotated[StudentService, Depends(get_student_service)]
