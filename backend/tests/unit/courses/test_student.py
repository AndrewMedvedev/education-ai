from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.courses.application.services.member import MemberService
from src.courses.domain.entities import Member
from src.courses.domain.vo import MemberRole
from src.shared.application.dtos import Page, Pagination
from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError


@pytest.fixture
def student_repo():
    """Создаёт мок репозитория записей студентов."""
    return AsyncMock()


@pytest.fixture
def course_repo():
    """Создаёт мок репозитория курсов."""
    return AsyncMock()


@pytest.fixture
def session():
    """Создаёт мок сессии базы данных."""
    return AsyncMock()


@pytest.fixture
def service(student_repo, course_repo, session):
    """Создаёт сервис студентов с изолированными зависимостями."""
    return MemberService(
        member_repo=student_repo,
        course_repo=course_repo,
        session=session,
    )


class TestStudentService:
    @pytest.mark.asyncio
    async def test_sign_course_creates_student(self, service, student_repo, course_repo, session):
        """Создаёт запись студента, если курс существует и записи ещё нет."""
        user_id = uuid4()
        course_id = uuid4()
        course_repo.exists.return_value = True
        student_repo.read.return_value = None

        student = await service.sign_course(user_id, course_id)

        assert student.user_id == user_id
        assert student.course_id == course_id
        created_student = student_repo.create.await_args.args[0]
        assert created_student == student
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sign_course_raises_when_course_not_found(
        self, service, student_repo, course_repo, session
    ):
        """Не создаёт запись студента для несуществующего курса."""
        course_repo.exists.return_value = False

        with pytest.raises(NotFoundError, match="Course with id .* not found"):
            await service.sign_course(uuid4(), uuid4())

        student_repo.read.assert_not_awaited()
        student_repo.create.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sign_course_raises_when_student_already_enrolled(
        self, service, student_repo, course_repo, session
    ):
        """Не создаёт повторную запись студента на одном курсе."""
        user_id = uuid4()
        course_id = uuid4()
        course_repo.exists.return_value = True
        student_repo.read.return_value = Member(
            user_id=user_id, course_id=course_id, role=MemberRole.STUDENT
        )

        with pytest.raises(AlreadyExistsError, match="already signed"):
            await service.sign_course(user_id, course_id)

        student_repo.create.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_my_courses_returns_repository_page(self, service, course_repo):
        """Возвращает страницу курсов, полученную из репозитория."""
        user_id = uuid4()
        pagination = Pagination(page=2, size=5)
        page = Page.create([], total=0, page=pagination.page, size=pagination.size)
        course_repo.find_member_courses.return_value = page

        result = await service.get_my_courses(user_id, pagination)

        assert result == page
        course_repo.find_member_courses.assert_awaited_once_with(user_id, pagination)
