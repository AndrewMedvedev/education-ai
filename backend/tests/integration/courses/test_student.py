from uuid import uuid4

import pytest

from src.courses.infra.database.repos.student import SqlStudentRepository
from src.courses.infra.models import StudentOrm
from src.shared.application.dtos import Pagination


@pytest.mark.asyncio
async def test_read_returns_only_matching_student_enrollment(session):
    """Находит запись студента только по совпадающей паре user и course."""
    user_id = uuid4()
    course_id = uuid4()
    enrollment = StudentOrm(user_id=user_id, course_id=course_id)
    other_enrollment = StudentOrm(user_id=uuid4(), course_id=course_id)
    session.add_all([enrollment, other_enrollment])
    await session.flush()
    repository = SqlStudentRepository(session)

    student = await repository.read(user_id, course_id)
    missing_student = await repository.read(uuid4(), course_id)

    assert student is not None
    assert student.id == enrollment.id
    assert missing_student is None


@pytest.mark.asyncio
async def test_find_by_course_returns_only_course_students_with_pagination(session):
    """Возвращает только студентов курса и корректные метаданные страницы."""
    course_id = uuid4()
    enrollments = [StudentOrm(user_id=uuid4(), course_id=course_id) for _ in range(3)]
    other_course_enrollment = StudentOrm(user_id=uuid4(), course_id=uuid4())
    session.add_all([*enrollments, other_course_enrollment])
    await session.flush()
    repository = SqlStudentRepository(session)

    page = await repository.find_by_course(course_id, Pagination(page=2, size=2))

    assert page.total == 3
    assert page.pages == 2
    assert page.has_prev is True
    assert page.has_next is False
    assert len(page.items) == 1
    assert page.items[0].course_id == course_id
