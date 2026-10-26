"""Idempotent direct-DB import for a platform course JSON file.

Run inside the backend container so the script uses the application's database
configuration and ORM. Existing course IDs are skipped unless --replace is set.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from src.core.database import session_factory
from src.courses.domain.enums import CourseStatus, DifficultyLevel
from src.courses.infra.database.models import CourseOrm, LessonOrm, ModuleOrm
from src.features.add_course import create_content_block


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
            select(CourseOrm).where(CourseOrm.id == course_id)
        )
        if existing and not replace:
            print(f"SKIPPED: course already exists: {course_id}")
            return course_id
        if existing:
            await session.delete(existing)
            await session.flush()

        course = CourseOrm(
            id=course_id,
            title=course_data["title"],
            description=course_data["description"],
            difficulty=DifficultyLevel(course_data["difficulty"]),
            status=CourseStatus(course_data.get("status", "draft")),
            tags=course_data.get("tags", []),
            learning_objectives=course_data.get("learning_objectives", []),
            creator_id=creator_id,
            image_url=course_data.get("image_url"),
            popularity=0,
        )
        session.add(course)

        for module_data in course_data.get("modules", []):
            module = ModuleOrm(
                id=UUID(module_data["id"]),
                course_id=course_id,
                title=module_data["title"],
                description=module_data["description"],
                order=module_data["order"],
                learning_objectives=module_data.get("learning_objectives", []),
            )
            session.add(module)
            for lesson_data in module_data.get("lessons", []):
                blocks = [
                    create_content_block(block)
                    for block in lesson_data.get("content_blocks", [])
                ]
                session.add(
                    LessonOrm(
                        id=UUID(lesson_data["id"]),
                        module_id=module.id,
                        title=lesson_data["title"],
                        description=lesson_data["description"],
                        order=lesson_data["order"],
                        learning_objectives=lesson_data.get("learning_objectives", []),
                        estimated_time_minutes=lesson_data.get(
                            "estimated_time_minutes"
                        ),
                        content_blocks=blocks,
                    )
                )

        await session.commit()
    print(f"IMPORTED: {course_data['title']} ({course_id})")
    return course_id


async def main() -> None:
    args = parse_args()
    await import_course(args.course_file, args.creator_id, args.replace)


if __name__ == "__main__":
    asyncio.run(main())
