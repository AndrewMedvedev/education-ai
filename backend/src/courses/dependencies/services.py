# pyright: reportArgumentType=false
from typing import Annotated

from uuid import UUID

from fastapi import Depends

from src.courses.application.repos import IAMRepository, OrganizationRepository
from src.courses.infra.external_apis import IAMClient, invite_user_in_organization
from src.shared.dependencies.database import DBSession, TransactionDep
from src.shared.domain.exceptions import NotFoundError

from ..application.check_access import CheckAccess
from ..application.repos import ProgressRepository
from ..application.services.course import CourseService
from ..application.services.document import DocumentService
from ..application.services.invitations import InvitationService
from ..application.services.lesson import LessonService
from ..application.services.member import MemberService
from ..application.services.module import ModuleService
from ..application.services.progress import LearningProgressService
from ..domain.entities import CourseProgress, LessonProgress, ModuleProgress
from ..infra.services import course_client
from .base import (
    CourseProgressRepoDep,
    CourseRepoDep,
    DocumentRepoDep,
    InvitationRepoDep,
    LessonProgressRepoDep,
    LessonRepoDep,
    MemberRepoDep,
    ModuleProgressRepoDep,
    ModuleRepoDep,
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


def get_check_course_access(
    course_repo: CourseRepoDep,
    member_repo: MemberRepoDep,
) -> CheckAccess:
    """Получает check access service, чтобы вызывающий код работал через единый интерфейс."""
    return CheckAccess(
        repo=course_repo,
        member_repo=member_repo,
    )


def get_check_module_access(
    member_repo: MemberRepoDep,
    module_repo: ModuleRepoDep,
) -> CheckAccess:
    """Получает check access service, чтобы вызывающий код работал через единый интерфейс."""
    return CheckAccess(
        member_repo=member_repo,
        repo=module_repo,
    )


def get_check_lesson_access(
    member_repo: MemberRepoDep,
    lesson_repo: LessonRepoDep,
) -> CheckAccess:
    """Получает check access service, чтобы вызывающий код работал через единый интерфейс."""
    return CheckAccess(
        member_repo=member_repo,
        repo=lesson_repo,
    )


def get_member_service(
    session: DBSession,
    member_repo: MemberRepoDep,
    course_repo: CourseRepoDep,
) -> MemberService:
    """Получает student service, чтобы вызывающий код работал через единый интерфейс."""
    return MemberService(member_repo=member_repo, session=session, course_repo=course_repo)


def get_iam_repo() -> IAMRepository:
    return IAMClient(course_client)


IAMRepoDep = Annotated[IAMRepository, Depends(get_iam_repo)]


def get_organization_repo() -> OrganizationRepository:
    return invite_user_in_organization


OrganizationRepoDep = Annotated[OrganizationRepository, Depends(get_organization_repo)]


def get_invitation_service(
    invitation_repo: InvitationRepoDep,
    course_repo: CourseRepoDep,
    member_repo: MemberRepoDep,
    transaction: TransactionDep,
    iam_repo: IAMRepoDep,
    organization_repo: OrganizationRepoDep,
) -> InvitationService:
    """Получает invitation service, чтобы вызывающий код работал через единый интерфейс."""
    return InvitationService(
        invitation_repo=invitation_repo,
        transaction=transaction,
        course_repo=course_repo,
        member_repo=member_repo,
        iam_repo=iam_repo,
        organization_repo=organization_repo,
        client=course_client,
    )


def get_learning_progress_service(
    session: DBSession,
    progress_repo: LessonProgressRepoDep,
    course_progress_repo: CourseProgressRepoDep,
    module_progress_repo: ModuleProgressRepoDep,
) -> LearningProgressService:
    """Возвращает сервис для управления прогрессом по урокам."""
    return LearningProgressService(
        progress_repo=progress_repo,
        course_progress_repo=course_progress_repo,
        module_progress_repo=module_progress_repo,
        session=session,
    )


async def get_progress[ProgressT: CourseProgress | ModuleProgress | LessonProgress](
    user_id: UUID,
    resource_id: UUID,
    repo: ProgressRepository[ProgressT],
) -> ProgressT:
    progress = await repo.get_by_user(user_id, resource_id)
    if progress is None:
        raise NotFoundError("Progress was not found")
    return progress


LessonServiceDep = Annotated[LessonService, Depends(get_lesson_service)]
ModuleServiceDep = Annotated[ModuleService, Depends(get_module_service)]
CourseServiceDep = Annotated[CourseService, Depends(get_course_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
MemberServiceDep = Annotated[MemberService, Depends(get_member_service)]
CheckCourseAccessDep = Annotated[CheckAccess, Depends(get_check_course_access)]
CheckModuleAccessDep = Annotated[CheckAccess, Depends(get_check_module_access)]
CheckLessonAccessDep = Annotated[CheckAccess, Depends(get_check_lesson_access)]
InvitationServiceDep = Annotated[InvitationService, Depends(get_invitation_service)]
LearningProgressServiceDep = Annotated[
    LearningProgressService, Depends(get_learning_progress_service)
]
