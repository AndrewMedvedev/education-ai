"""Idempotent direct-DB import for a platform course JSON file.

Run inside the backend container so the script uses the application's database
configuration and ORM. Existing entities are updated by their stable IDs.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

# When launched as ``python scripts/import_course_json.py``, Python places
# ``/app/scripts`` (not ``/app``) on sys.path. Add the backend root so imports
# from the application's ``src`` package work both locally and in Docker.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select  # noqa: E402

from src.core.database import session_factory  # noqa: E402
from src.courses.domain.enums import CourseStatus, DifficultyLevel  # noqa: E402
from src.courses.infra.database.models import CourseOrm, LessonOrm, ModuleOrm  # noqa: E402
from src.courses.infra.database.types import block_from_dict  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import a course directly into PostgreSQL."
    )
    parser.add_argument(
        "--course-file", type=Path, required=True, help="Path inside backend container"
    )
    parser.add_argument(
        "--creator-id", type=UUID, required=True, help="Existing platform user UUID"
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace a course with the same course.id",
    )
    return parser.parse_args()


async def import_course(course_file: Path, creator_id: UUID, replace: bool) -> UUID:
    payload = json.loads(course_file.read_text(encoding="utf-8"))
    course_data = payload["course"]
    course_id = UUID(course_data["id"])

    async with session_factory() as session:
        existing = await session.scalar(
            select(CourseOrm).where(CourseOrm.id == course_id).with_for_update()
        )
        updated = existing is not None and not replace
        if existing and replace:
            await session.delete(existing)
            await session.flush()
            existing = None

        if existing is None:
            existing = CourseOrm(id=course_id, creator_id=creator_id, popularity=0)
            session.add(existing)
        existing.title = course_data["title"]
        existing.description = course_data["description"]
        existing.difficulty = DifficultyLevel(course_data["difficulty"])
        existing.status = CourseStatus(course_data.get("status", "draft"))
        existing.tags = course_data.get("tags", [])
        existing.learning_objectives = course_data.get("learning_objectives", [])
        existing.image_url = course_data.get("image_url")
        await session.flush()

        module_ids = set()
        lesson_ids = set()
        for module_data in course_data.get("modules", []):
            module_id = UUID(module_data["id"])
            if module_id in module_ids:
                raise ValueError(f"Duplicate module ID: {module_id}")
            module_ids.add(module_id)
            module = await session.get(ModuleOrm, module_id)
            if module is None:
                module = ModuleOrm(id=module_id, course_id=course_id)
                session.add(module)
            elif module.course_id != course_id:
                raise ValueError(f"Module {module_id} belongs to another course")
            module.title = module_data["title"]
            module.description = module_data["description"]
            module.order = module_data["order"]
            module.learning_objectives = module_data.get("learning_objectives", [])
            await session.flush()

            for lesson_data in module_data.get("lessons", []):
                lesson_id = UUID(lesson_data["id"])
                if lesson_id in lesson_ids:
                    raise ValueError(f"Duplicate lesson ID: {lesson_id}")
                lesson_ids.add(lesson_id)
                lesson = await session.get(LessonOrm, lesson_id)
                if lesson is None:
                    lesson = LessonOrm(id=lesson_id, module_id=module_id)
                    session.add(lesson)
                elif lesson.module_id != module_id:
                    raise ValueError(f"Lesson {lesson_id} belongs to another module")
                blocks = [
                    block_from_dict(block)
                    for block in lesson_data.get("content_blocks", [])
                ]
                lesson.title = lesson_data["title"]
                lesson.description = lesson_data["description"]
                lesson.order = lesson_data["order"]
                lesson.learning_objectives = lesson_data.get("learning_objectives", [])
                lesson.estimated_time_minutes = lesson_data.get(
                    "estimated_time_minutes"
                )
                lesson.content_blocks = blocks

        await session.commit()
    action = "UPDATED" if updated else "IMPORTED"
    print(f"{action}: {course_data['title']} ({course_id})")
    return course_id


async def main() -> None:
    args = parse_args()
    await import_course(args.course_file, args.creator_id, args.replace)


if __name__ == "__main__":
    asyncio.run(main())
