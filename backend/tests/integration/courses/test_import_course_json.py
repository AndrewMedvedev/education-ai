import json
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from scripts import import_course_json as importer
from src.core.database import Base
from src.courses.infra.database.models import (
    CourseOrm,
    CourseProgressOrm,
    LessonOrm,
    LessonProgressOrm,
    LessonTheorySessionOrm,
    ModuleOrm,
    ModuleProgressOrm,
    PracticeOrm,
)
from src.courses.domain.enums import PracticeStatus


@pytest_asyncio.fixture
async def session():
    url = os.environ.get("COURSE_IMPORT_TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "Set COURSE_IMPORT_TEST_DATABASE_URL to a disposable PostgreSQL database"
        )
    schema = f"course_import_test_{uuid4().hex}"
    admin_engine = create_async_engine(url)
    async with admin_engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(
        url, connect_args={"server_settings": {"search_path": schema}}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as test_session:
        yield test_session
    await engine.dispose()
    async with admin_engine.begin() as connection:
        await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    await admin_engine.dispose()


def make_payload():
    lesson = {
        "id": str(uuid4()),
        "title": "Lesson",
        "description": "Description",
        "order": 1,
        "content_blocks": [{"content_type": "text", "md_content": "Before"}],
    }
    module = {
        "id": str(uuid4()),
        "title": "Module",
        "description": "Description",
        "order": 1,
        "lessons": [lesson],
    }
    return {
        "course": {
            "id": str(uuid4()),
            "title": "Course",
            "description": "Description",
            "difficulty": "beginner",
            "status": "published",
            "modules": [module],
        }
    }


@pytest.fixture
def import_session(monkeypatch, session):
    @asynccontextmanager
    async def factory():
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

    monkeypatch.setattr(importer, "session_factory", factory)
    return session


@pytest.mark.asyncio
async def test_import_updates_and_adds_without_losing_progress(
    import_session, tmp_path, capsys
):
    payload = make_payload()
    path = tmp_path / "course.json"
    creator = uuid4()
    path.write_text(json.dumps(payload), encoding="utf-8")
    await importer.import_course(path, creator, False)

    course_data = payload["course"]
    module_data = course_data["modules"][0]
    lesson_data = module_data["lessons"][0]
    course_id, lesson_id = UUID(course_data["id"]), UUID(lesson_data["id"])
    progress = CourseProgressOrm(
        user_id=uuid4(), course_id=course_id, progress_percent=50
    )
    theory = LessonTheorySessionOrm(user_id=uuid4(), lesson_id=lesson_id)
    import_session.add_all([progress, theory])
    await import_session.commit()
    progress_id, theory_id = progress.id, theory.id

    course_data["title"] = "Updated course"
    module_data["title"] = "Updated module"
    lesson_data["title"] = "Updated lesson"
    lesson_data["content_blocks"] = [{"content_type": "text", "md_content": "After"}]
    module_data["lessons"].append(
        {
            "id": str(uuid4()),
            "title": "New lesson",
            "description": "New",
            "order": 2,
            "content_blocks": [],
        }
    )
    path.write_text(json.dumps(payload), encoding="utf-8")
    await importer.import_course(path, uuid4(), False)
    await importer.import_course(path, uuid4(), False)
    import_session.expire_all()

    course = await import_session.get(CourseOrm, course_id)
    module = await import_session.get(ModuleOrm, UUID(module_data["id"]))
    lesson = await import_session.get(LessonOrm, lesson_id)
    assert course.title == "Updated course" and course.creator_id == creator
    assert module.title == "Updated module"
    assert (
        lesson.title == "Updated lesson"
        and lesson.content_blocks[0].md_content == "After"
    )
    assert await import_session.scalar(select(func.count()).select_from(LessonOrm)) == 2
    assert await import_session.get(CourseProgressOrm, progress_id) is not None
    assert await import_session.get(LessonTheorySessionOrm, theory_id) is not None
    assert "UPDATED:" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_conflicting_order_rolls_back_all_changes(import_session, tmp_path):
    payload = make_payload()
    path = tmp_path / "course.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    await importer.import_course(path, uuid4(), False)
    course_data = payload["course"]
    course_data["title"] = "Must roll back"
    course_data["modules"][0]["lessons"].append(
        {
            "id": str(uuid4()),
            "title": "Conflict",
            "description": "",
            "order": 1,
            "content_blocks": [],
        }
    )
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(Exception, match="uq_lesson_module_order"):
        await importer.import_course(path, uuid4(), False)
    course = await import_session.get(CourseOrm, UUID(course_data["id"]))
    assert course.title == "Course"
    assert await import_session.scalar(select(func.count()).select_from(LessonOrm)) == 1


@pytest.mark.asyncio
async def test_reordering_modules_and_lessons(import_session, tmp_path):
    payload = make_payload()
    first = payload["course"]["modules"][0]
    second_lesson = dict(first["lessons"][0], id=str(uuid4()), order=2)
    first["lessons"].append(second_lesson)
    second = dict(first, id=str(uuid4()), order=2, lessons=[])
    payload["course"]["modules"].append(second)
    path = tmp_path / "course.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    await importer.import_course(path, uuid4(), False)
    first["order"], second["order"] = 2, 1
    first["lessons"][0]["order"], second_lesson["order"] = 2, 1
    path.write_text(json.dumps(payload), encoding="utf-8")
    await importer.import_course(path, uuid4(), False)
    import_session.expire_all()
    assert (await import_session.get(ModuleOrm, UUID(first["id"]))).order == 2
    assert (await import_session.get(LessonOrm, UUID(second_lesson["id"]))).order == 1


@pytest.mark.asyncio
async def test_move_lesson_preserves_progress_and_practice(import_session, tmp_path):
    payload = make_payload()
    course = payload["course"]
    source = course["modules"][0]
    lesson = source["lessons"][0]
    target = dict(source, id=str(uuid4()), title="Target", order=2, lessons=[])
    course["modules"].append(target)
    path = tmp_path / "course.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    await importer.import_course(path, uuid4(), False)

    user_id, course_id, lesson_id = uuid4(), UUID(course["id"]), UUID(lesson["id"])
    course_progress = CourseProgressOrm(
        user_id=user_id, course_id=course_id, progress_percent=50
    )
    import_session.add(course_progress)
    await import_session.flush()
    module_progress = ModuleProgressOrm(
        course_progress_id=course_progress.id, module_id=UUID(source["id"])
    )
    import_session.add(module_progress)
    await import_session.flush()
    completed = datetime(2026, 1, 1, tzinfo=UTC)
    lesson_progress = LessonProgressOrm(
        module_progress_id=module_progress.id,
        lesson_id=lesson_id,
        theory_completed_at=completed,
    )
    practice = PracticeOrm(
        user_id=user_id,
        module_id=UUID(source["id"]),
        lesson_id=lesson_id,
        status=PracticeStatus.COMPLETED,
        practice=[],
    )
    import_session.add_all([lesson_progress, practice])
    await import_session.commit()
    progress_id, practice_id = lesson_progress.id, practice.id
    source["lessons"] = []
    target["lessons"] = [lesson]
    path.write_text(json.dumps(payload), encoding="utf-8")
    await importer.import_course(path, uuid4(), False)
    await importer.import_course(path, uuid4(), False)
    import_session.expire_all()

    moved = await import_session.get(LessonOrm, lesson_id)
    progress = await import_session.get(LessonProgressOrm, progress_id)
    destination = await import_session.get(
        ModuleProgressOrm, progress.module_progress_id
    )
    moved_practice = await import_session.get(PracticeOrm, practice_id)
    assert moved.module_id == UUID(target["id"])
    assert destination.module_id == moved.module_id
    assert progress.theory_completed_at == completed
    assert moved_practice.module_id == moved.module_id
    assert (
        await import_session.scalar(select(func.count()).select_from(LessonProgressOrm))
        == 1
    )


@pytest.mark.asyncio
async def test_move_from_other_course_is_rejected(import_session, tmp_path):
    original, other = make_payload(), make_payload()
    path = tmp_path / "course.json"
    path.write_text(json.dumps(original), encoding="utf-8")
    await importer.import_course(path, uuid4(), False)
    other["course"]["modules"][0]["lessons"] = original["course"]["modules"][0][
        "lessons"
    ]
    path.write_text(json.dumps(other), encoding="utf-8")
    with pytest.raises(ValueError, match="another course"):
        await importer.import_course(path, uuid4(), False)
    assert await import_session.get(CourseOrm, UUID(other["course"]["id"])) is None
