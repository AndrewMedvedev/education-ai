from typing import Annotated

from fastapi import Depends
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.shared.dependencies.database import DBSession

from ..infra.database.repos.chat import SqlChatRepository
from ..infra.database.repos.course import SqlCourseRepository
from ..infra.database.repos.document import SqlDocumentRepository
from ..infra.database.repos.lesson import SqlLessonRepository
from ..infra.database.repos.module import SqlModuleRepository
from ..infra.database.repos.practice import SqlPracticeRepository
from ..infra.database.repos.student import SqlStudentRepository
from ..infra.database.repos.theory_session import SqlLessonTheorySessionRepository

splitter = RecursiveCharacterTextSplitter(chunk_size=3072, chunk_overlap=150, length_function=len)


def get_lesson_repo(session: DBSession) -> SqlLessonRepository:
    """Получает lesson repo, чтобы вызывающий код работал через единый интерфейс."""
    return SqlLessonRepository(session)


def get_module_repo(session: DBSession) -> SqlModuleRepository:
    """Получает module repo, чтобы вызывающий код работал через единый интерфейс."""
    return SqlModuleRepository(session)


def get_course_repo(session: DBSession) -> SqlCourseRepository:
    """Получает course repo, чтобы вызывающий код работал через единый интерфейс."""
    return SqlCourseRepository(session)


def get_practice_repo(session: DBSession) -> SqlPracticeRepository:
    """Получает chat repo, чтобы вызывающий код работал через единый интерфейс."""
    return SqlPracticeRepository(session)


def get_chat_repo(session: DBSession) -> SqlChatRepository:
    """Получает chat repo, чтобы вызывающий код работал через единый интерфейс."""
    return SqlChatRepository(session)


def get_document_repo(session: DBSession) -> SqlDocumentRepository:
    """Получает document repo, чтобы вызывающий код работал через единый интерфейс."""
    return SqlDocumentRepository(session)


def get_theory_session_repo(session: DBSession) -> SqlLessonTheorySessionRepository:
    """Получает theory session repo, чтобы вызывающий код работал через единый интерфейс."""
    return SqlLessonTheorySessionRepository(session)


def get_student_repo(session: DBSession) -> SqlStudentRepository:
    """Получает student repo, чтобы вызывающий код работал через единый интерфейс."""
    return SqlStudentRepository(session)


LessonRepoDep = Annotated[SqlLessonRepository, Depends(get_lesson_repo)]
ModuleRepoDep = Annotated[SqlModuleRepository, Depends(get_module_repo)]
CourseRepoDep = Annotated[SqlCourseRepository, Depends(get_course_repo)]
PracticeRepoDep = Annotated[SqlPracticeRepository, Depends(get_practice_repo)]
ChatRepoDep = Annotated[SqlChatRepository, Depends(get_chat_repo)]
DocumentRepoDep = Annotated[SqlDocumentRepository, Depends(get_document_repo)]
TheorySessionRepoDep = Annotated[
    SqlLessonTheorySessionRepository, Depends(get_theory_session_repo)
]
StudentRepoDep = Annotated[SqlStudentRepository, Depends(get_student_repo)]
