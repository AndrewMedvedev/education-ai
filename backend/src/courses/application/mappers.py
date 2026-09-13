from typing import Any, cast

from dataclasses import asdict
from datetime import datetime

from pydantic import BaseModel

from ..domain.constants import _BLOCK_REGISTRY
from ..domain.entities import AnyContentBlock, Course, Lesson, Module, Question, QuizBlock
from ..domain.vo import ExtendedContentType
from .domain_dtos import (
    AnyContentBlockDict,
    ChemicalBlockDict,
    CodeBlockDict,
    CourseDict,
    LessonDict,
    MathBlockDict,
    MermaidBlockDict,
    ModuleDict,
    MusicalBlockDict,
    QuizBlockDict,
    TextBlockDict,
    VideoBlockDict,
)

_BLOCK_REGISTRY_DICT: dict[str, type[AnyContentBlockDict]] = {
    ExtendedContentType.TEXT: TextBlockDict,
    ExtendedContentType.VIDEO: VideoBlockDict,
    ExtendedContentType.PROGRAM_CODE: CodeBlockDict,
    ExtendedContentType.QUIZ: QuizBlockDict,
    ExtendedContentType.MERMAID: MermaidBlockDict,
    ExtendedContentType.MATH_FORMULA: MathBlockDict,
    ExtendedContentType.CHEMICAL_FORMULA: ChemicalBlockDict,
    ExtendedContentType.MUSICAL_NOTATION: MusicalBlockDict,
}


def model_to_typed_dict[DictT](model: BaseModel) -> DictT:
    return cast(
        DictT,
        model.model_dump(mode="json"),
    )


def typed_dict_to_model[ModelT: BaseModel](
    data: dict[str, Any],
    model_type: type[ModelT],
) -> ModelT:

    return model_type.model_validate(data)


def _to_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value

    return datetime.fromisoformat(value)


def dict_to_content_block(data: AnyContentBlockDict) -> AnyContentBlock:

    content_type = data["content_type"]

    # потому что questions должны стать Question, а не остаться dict.

    if content_type == ExtendedContentType.QUIZ:
        return QuizBlock(
            ai_generated=data["ai_generated"],
            questions=[
                Question(
                    question=question["question"],
                    answer=question["answer"],
                )
                for question in data["questions"]  # pyright: ignore[reportGeneralTypeIssues]
            ],
        )

    block_class = _BLOCK_REGISTRY[content_type]

    kwargs = dict(data)

    kwargs.pop("content_type", None)

    return block_class(**kwargs)  # pyright: ignore[reportArgumentType]


def course_to_dict(course: Course) -> CourseDict:
    return {
        "id": course.id,
        "created_at": course.created_at,
        "updated_at": course.updated_at,
        "deleted_at": course.deleted_at,
        "title": course.title,
        "description": course.description,
        "difficulty": course.difficulty,
        "tags": course.tags,
        "status": course.status,
        "popularity": course.popularity,
        "creator_id": course.creator_id,
        "image_url": course.image_url,
        "learning_objectives": course.learning_objectives,
        "modules": [module_to_dict(module) for module in course.modules],
    }


def dict_to_course(data: CourseDict) -> Course:
    return Course(
        id=data["id"],
        created_at=_to_datetime(data["created_at"]),
        updated_at=_to_datetime(data["updated_at"]),
        deleted_at=_to_datetime(data["deleted_at"]) if data["deleted_at"] else None,
        title=data["title"],
        description=data["description"],
        difficulty=data["difficulty"],
        tags=data["tags"],
        status=data["status"],
        popularity=data["popularity"],
        creator_id=data["creator_id"],
        image_url=data["image_url"],
        learning_objectives=data["learning_objectives"],
        modules=[dict_to_module(module) for module in data["modules"]],
    )


def module_to_dict(module: Module) -> ModuleDict:
    return {
        "id": module.id,
        "created_at": module.created_at,
        "updated_at": module.updated_at,
        "deleted_at": module.deleted_at,
        "course_id": module.course_id,
        "title": module.title,
        "description": module.description,
        "order": module.order,
        "learning_objectives": module.learning_objectives,
        "lessons": [lesson_to_dict(lesson) for lesson in module.lessons],
    }


def dict_to_module(data: ModuleDict) -> Module:
    return Module(
        id=data["id"],
        created_at=_to_datetime(data["created_at"]),
        updated_at=_to_datetime(data["updated_at"]),
        deleted_at=_to_datetime(data["deleted_at"]) if data["deleted_at"] else None,
        course_id=data["course_id"],
        title=data["title"],
        description=data["description"],
        order=data["order"],
        learning_objectives=data["learning_objectives"],
        lessons=[dict_to_lesson(lesson) for lesson in data["lessons"]],
    )


def lesson_to_dict(lesson: Lesson) -> LessonDict:
    return {
        "id": lesson.id,
        "created_at": lesson.created_at,
        "updated_at": lesson.updated_at,
        "deleted_at": lesson.deleted_at,
        "module_id": lesson.module_id,
        "title": lesson.title,
        "description": lesson.description,
        "order": lesson.order,
        "learning_objectives": lesson.learning_objectives,
        "content_blocks": [
            cast(AnyContentBlockDict, asdict(block)) for block in lesson.content_blocks
        ],
        "estimated_time_minutes": lesson.estimated_time_minutes,
    }


def dict_to_lesson(data: LessonDict) -> Lesson:
    return Lesson(
        id=data["id"],
        created_at=_to_datetime(data["created_at"]),
        updated_at=_to_datetime(data["updated_at"]),
        deleted_at=_to_datetime(data["deleted_at"]) if data["deleted_at"] else None,
        module_id=data["module_id"],
        title=data["title"],
        description=data["description"],
        order=data["order"],
        learning_objectives=data["learning_objectives"],
        content_blocks=[dict_to_content_block(block) for block in data["content_blocks"]],
        estimated_time_minutes=data["estimated_time_minutes"],
    )
