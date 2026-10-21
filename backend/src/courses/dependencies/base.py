from typing import Annotated

from fastapi import Depends
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.qdrant import qdrant_client
from src.courses.infra.database.repos.vector_repo import QdrantRepository
from src.shared.dependencies.database import DBSession

from ..infra.database.repos.chat import SqlChatRepository
from ..infra.database.repos.course import SqlCourseRepository
from ..infra.database.repos.course_progress import SqlCourseProgressRepository
from ..infra.database.repos.document import SqlDocumentRepository
from ..infra.database.repos.invitation import SqlInvitationRepository
from ..infra.database.repos.lesson import SqlLessonRepository
from ..infra.database.repos.lesson_progress import SqlLessonProgressRepository
from ..infra.database.repos.member import SqlMemberRepository
from ..infra.database.repos.module import SqlModuleRepository
from ..infra.database.repos.module_progress import SqlModuleProgressRepository
from ..infra.database.repos.practice import SqlPracticeRepository
from ..infra.database.repos.theory_session import SqlLessonTheorySessionRepository

splitter = RecursiveCharacterTextSplitter(chunk_size=3072, chunk_overlap=150, length_function=len)


def get_lesson_repo(session: DBSession) -> SqlLessonRepository:
    """Получает lesson repo, чтобы вызывающий код работал через единый интерфейс."""
    return SqlLessonRepository(session)


def get_lesson_progress_repo(session: DBSession) -> SqlLessonProgressRepository:
    """Возвращает репозиторий для работы с прогрессом уроков."""
    return SqlLessonProgressRepository(session)


def get_module_progress_repo(session: DBSession) -> SqlModuleProgressRepository:
    """Возвращает репозиторий для работы с прогрессом модулей."""
    return SqlModuleProgressRepository(session)


def get_course_progress_repo(session: DBSession) -> SqlCourseProgressRepository:
    """Возвращает репозиторий для работы с прогрессом курсов."""
    return SqlCourseProgressRepository(session)


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


def get_member_repo(session: DBSession) -> SqlMemberRepository:
    """Получает student repo, чтобы вызывающий код работал через единый интерфейс."""
    return SqlMemberRepository(session)


def get_invitation_repo(session: DBSession) -> SqlInvitationRepository:
    """Получает invitation repo, чтобы вызывающий код работал через единый интерфейс."""
    return SqlInvitationRepository(session)


def get_vector_repo() -> QdrantRepository:
    return QdrantRepository(qdrant_client, splitter)


LessonRepoDep = Annotated[SqlLessonRepository, Depends(get_lesson_repo)]
LessonProgressRepoDep = Annotated[
    SqlLessonProgressRepository, Depends(get_lesson_progress_repo)
]
ModuleProgressRepoDep = Annotated[
    SqlModuleProgressRepository, Depends(get_module_progress_repo)
]
CourseProgressRepoDep = Annotated[
    SqlCourseProgressRepository, Depends(get_course_progress_repo)
]
ModuleRepoDep = Annotated[SqlModuleRepository, Depends(get_module_repo)]
CourseRepoDep = Annotated[SqlCourseRepository, Depends(get_course_repo)]
PracticeRepoDep = Annotated[SqlPracticeRepository, Depends(get_practice_repo)]
ChatRepoDep = Annotated[SqlChatRepository, Depends(get_chat_repo)]
DocumentRepoDep = Annotated[SqlDocumentRepository, Depends(get_document_repo)]
TheorySessionRepoDep = Annotated[
    SqlLessonTheorySessionRepository, Depends(get_theory_session_repo)
]
MemberRepoDep = Annotated[SqlMemberRepository, Depends(get_member_repo)]
InvitationRepoDep = Annotated[SqlInvitationRepository, Depends(get_invitation_repo)]
VectorRepoDep = Annotated[QdrantRepository, Depends(get_vector_repo)]
