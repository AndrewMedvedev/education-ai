from uuid import uuid4

import pytest

from src.courses.domain.enums import CourseStatus, DifficultyLevel
from src.courses.infra.database.repos.course import SqlCourseRepository
from src.courses.infra.models import CourseOrm, ModuleOrm, StudentOrm
from src.shared.application.dtos import Pagination


@pytest.mark.asyncio
async def test_get_by_id_basic_info_returns_course_with_modules(session):
    """Возвращает краткие данные курса вместе с его модулями из базы данных."""
    course_id = uuid4()
    course = CourseOrm(
        id=course_id,
        creator_id=uuid4(),
        title="Python",
        description="Python course",
        difficulty=DifficultyLevel.BEGINNER,
        tags=["python"],
        status=CourseStatus.PUBLISHED,
        learning_objectives=["Learn Python"],
    )
    module = ModuleOrm(
        id=uuid4(),
        course_id=course_id,
        title="Basics",
        description="Python basics",
        order=1,
        learning_objectives=["Learn syntax"],
    )
    session.add_all([course, module])
    await session.flush()
    repository = SqlCourseRepository(session)

    basic_info = await repository.get_by_id_basic_info(course_id)

    assert basic_info is not None
    assert basic_info.id == course_id
    assert basic_info.title == "Python"
    assert basic_info.modules[0].id == module.id
    assert basic_info.modules[0].title == "Basics"


@pytest.mark.asyncio
async def test_get_by_id_basic_info_returns_modules_in_course_order(session):
    """Возвращает модули курса в порядке их позиции в программе."""
    course = CourseOrm(
        id=uuid4(),
        creator_id=uuid4(),
        title="Python",
        description="Python course",
        difficulty=DifficultyLevel.BEGINNER,
        tags=["python"],
        status=CourseStatus.PUBLISHED,
    )
    later_module = ModuleOrm(
        id=uuid4(),
        course_id=course.id,
        title="Advanced",
        description="Advanced Python",
        order=2,
    )
    first_module = ModuleOrm(
        id=uuid4(),
        course_id=course.id,
        title="Basics",
        description="Python basics",
        order=1,
    )
    session.add_all([course, later_module, first_module])
    await session.flush()
    repository = SqlCourseRepository(session)

    basic_info = await repository.get_by_id_basic_info(course.id)

    assert basic_info is not None
    assert [module.id for module in basic_info.modules] == [first_module.id, later_module.id]


@pytest.mark.asyncio
async def test_get_by_id_basic_info_returns_none_for_unknown_course(session):
    """Не возвращает базовые данные для отсутствующего курса."""
    repository = SqlCourseRepository(session)

    assert await repository.get_by_id_basic_info(uuid4()) is None


@pytest.mark.asyncio
async def test_get_by_id_basic_info_returns_empty_modules_for_new_course(session):
    """Возвращает пустую программу для курса, в который еще не добавили модули."""
    course = CourseOrm(
        id=uuid4(),
        creator_id=uuid4(),
        title="Python",
        description="Python course",
        difficulty=DifficultyLevel.BEGINNER,
        tags=["python"],
        status=CourseStatus.DRAFT,
    )
    session.add(course)
    await session.flush()
    repository = SqlCourseRepository(session)

    basic_info = await repository.get_by_id_basic_info(course.id)

    assert basic_info is not None
    assert basic_info.modules == []


@pytest.mark.asyncio
async def test_find_student_courses_excludes_archived_courses(session):
    """Возвращает ученику только доступные курсы, на которые он записан."""
    user_id = uuid4()
    published_course = CourseOrm(
        id=uuid4(),
        creator_id=uuid4(),
        title="Published Python",
        description="Published course",
        difficulty=DifficultyLevel.BEGINNER,
        tags=["python"],
        status=CourseStatus.PUBLISHED,
    )
    archived_course = CourseOrm(
        id=uuid4(),
        creator_id=uuid4(),
        title="Archived Python",
        description="Archived course",
        difficulty=DifficultyLevel.BEGINNER,
        tags=["python"],
        status=CourseStatus.ARCHIVED,
    )
    session.add_all(
        [
            published_course,
            archived_course,
            StudentOrm(course_id=published_course.id, user_id=user_id),
            StudentOrm(course_id=archived_course.id, user_id=user_id),
        ]
    )
    await session.flush()
    repository = SqlCourseRepository(session)

    page = await repository.find_student_courses(user_id, Pagination())

    assert [course.id for course in page.items] == [published_course.id]


@pytest.mark.asyncio
async def test_find_returns_only_published_courses(session):
    """Возвращает в публичном списке только опубликованные курсы."""
    published_course = CourseOrm(
        id=uuid4(),
        creator_id=uuid4(),
        title="Published Python",
        description="Published course",
        difficulty=DifficultyLevel.BEGINNER,
        tags=["python"],
        status=CourseStatus.PUBLISHED,
    )
    draft_course = CourseOrm(
        id=uuid4(),
        creator_id=uuid4(),
        title="Draft Python",
        description="Draft course",
        difficulty=DifficultyLevel.BEGINNER,
        tags=["python"],
        status=CourseStatus.DRAFT,
    )
    session.add_all([published_course, draft_course])
    await session.flush()
    repository = SqlCourseRepository(session)

    page = await repository.find(Pagination())

    assert [course.id for course in page.items] == [published_course.id]


@pytest.mark.asyncio
async def test_find_returns_page_metadata_for_published_courses(session):
    """Возвращает корректные метаданные второй страницы опубликованных курсов."""
    courses = [
        CourseOrm(
            id=uuid4(),
            creator_id=uuid4(),
            title=f"Python {number}",
            description="Published course",
            difficulty=DifficultyLevel.BEGINNER,
            tags=["python"],
            status=CourseStatus.PUBLISHED,
        )
        for number in range(3)
    ]
    session.add_all(courses)
    await session.flush()
    repository = SqlCourseRepository(session)

    page = await repository.find(Pagination(page=2, size=2))

    assert page.total == 3
    assert page.pages == 2
    assert page.has_prev is True
    assert page.has_next is False
    assert len(page.items) == 1


@pytest.mark.asyncio
async def test_find_user_courses_returns_only_creator_courses(session):
    """Возвращает создателю только принадлежащие ему курсы."""
    creator_id = uuid4()
    creator_course = CourseOrm(
        id=uuid4(),
        creator_id=creator_id,
        title="Creator Python",
        description="Creator course",
        difficulty=DifficultyLevel.BEGINNER,
        tags=["python"],
        status=CourseStatus.DRAFT,
    )
    other_course = CourseOrm(
        id=uuid4(),
        creator_id=uuid4(),
        title="Other Python",
        description="Other course",
        difficulty=DifficultyLevel.BEGINNER,
        tags=["python"],
        status=CourseStatus.DRAFT,
    )
    session.add_all([creator_course, other_course])
    await session.flush()
    repository = SqlCourseRepository(session)

    page = await repository.find_user_courses(creator_id, Pagination())

    assert [course.id for course in page.items] == [creator_course.id]


@pytest.mark.asyncio
async def test_get_course_status_returns_status_only_for_creator(session):
    """Возвращает статус курса его создателю."""
    creator_id = uuid4()
    course = CourseOrm(
        id=uuid4(),
        creator_id=creator_id,
        title="Python",
        description="Python course",
        difficulty=DifficultyLevel.BEGINNER,
        tags=["python"],
        status=CourseStatus.PUBLISHED,
    )
    session.add(course)
    await session.flush()
    repository = SqlCourseRepository(session)

    status = await repository.get_course_status(course.id, creator_id)

    assert status == CourseStatus.PUBLISHED


@pytest.mark.asyncio
async def test_get_course_status_returns_none_for_other_creator(session):
    """Не возвращает статус курса пользователю, который его не создавал."""
    course = CourseOrm(
        id=uuid4(),
        creator_id=uuid4(),
        title="Python",
        description="Python course",
        difficulty=DifficultyLevel.BEGINNER,
        tags=["python"],
        status=CourseStatus.PUBLISHED,
    )
    session.add(course)
    await session.flush()
    repository = SqlCourseRepository(session)

    status = await repository.get_course_status(course.id, uuid4())

    assert status is None


@pytest.mark.asyncio
async def test_get_course_status_returns_none_for_unknown_course(session):
    """Не возвращает статус, когда курса с указанным идентификатором нет."""
    repository = SqlCourseRepository(session)

    assert await repository.get_course_status(uuid4(), uuid4()) is None
