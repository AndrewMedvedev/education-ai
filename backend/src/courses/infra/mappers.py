# pyright: reportArgumentType=false, reportAttributeAccessIssue=false


import logging

from src.shared.infra.database.mappers import ModelMapper

from ..domain.entities import (
    BasicInfo,
    Chat,
    Course,
    CourseBasicInfo,
    Document,
    Lesson,
    LessonBasicInfo,
    LessonTheorySession,
    Module,
    ModuleBasicInfo,
    Practice,
    Student,
)
from .models import (
    ChatOrm,
    CourseOrm,
    DocumentOrm,
    LessonOrm,
    LessonTheorySessionOrm,
    ModuleOrm,
    PracticeOrm,
    StudentOrm,
)

logger = logging.getLogger(__name__)


class ChatMapper(ModelMapper[Chat, ChatOrm]):
    @staticmethod
    def from_model(model: ChatOrm) -> Chat:

        return Chat(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            user_id=model.user_id,
            course_id=model.course_id,
            messages=model.messages,
        )

    @staticmethod
    def to_model(entity: Chat) -> ChatOrm:

        return ChatOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            user_id=entity.user_id,
            course_id=entity.course_id,
            messages=entity.messages,
        )


class LessonMapper(ModelMapper[Lesson, LessonOrm]):
    @staticmethod
    def from_model(model: LessonOrm) -> Lesson:

        return Lesson(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            module_id=model.module_id,
            title=model.title,
            description=model.description,
            order=model.order,
            learning_objectives=model.learning_objectives,
            content_blocks=model.content_blocks,
            estimated_time_minutes=model.estimated_time_minutes,
        )

    @staticmethod
    def to_model(entity: Lesson) -> LessonOrm:
        return LessonOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            module_id=entity.module_id,
            title=entity.title,
            description=entity.description,
            order=entity.order,
            learning_objectives=entity.learning_objectives,
            content_blocks=entity.content_blocks,
            estimated_time_minutes=entity.estimated_time_minutes,
        )

    @staticmethod
    def basic_info_mapper(row: tuple) -> LessonBasicInfo:
        return LessonBasicInfo(
            id=row.id,
            title=row.title,
            description=row.description,
            order=row.order,
            learning_objectives=row.learning_objectives,
            estimated_time_minutes=row.estimated_time_minutes,
        )


class ModuleMapper(ModelMapper[Module, ModuleOrm]):
    @staticmethod
    def from_model(model: ModuleOrm) -> Module:
        return Module(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            course_id=model.course_id,
            title=model.title,
            description=model.description,
            order=model.order,
            learning_objectives=model.learning_objectives,
        )

    @staticmethod
    def to_model(entity: Module) -> ModuleOrm:
        return ModuleOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            course_id=entity.course_id,
            title=entity.title,
            description=entity.description,
            order=entity.order,
            learning_objectives=entity.learning_objectives,
        )

    @staticmethod
    def basic_info_mapper(row: tuple, lessons: list[BasicInfo]) -> ModuleBasicInfo:
        return ModuleBasicInfo(
            id=row.id,
            title=row.title,
            description=row.description,
            order=row.order,
            learning_objectives=row.learning_objectives,
            lessons=lessons,
        )


class CourseMapper(ModelMapper[Course, CourseOrm]):
    @staticmethod
    def from_model(model: CourseOrm) -> Course:
        return Course(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            title=model.title,
            description=model.description,
            difficulty=model.difficulty,
            tags=model.tags,
            status=model.status,
            popularity=model.popularity,
            creator_id=model.creator_id,
            image_url=model.image_url,
            learning_objectives=model.learning_objectives,
        )

    @staticmethod
    def to_model(entity: Course) -> CourseOrm:
        return CourseOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            title=entity.title,
            description=entity.description,
            difficulty=entity.difficulty,
            tags=entity.tags,
            status=entity.status,
            popularity=entity.popularity,
            creator_id=entity.creator_id,
            image_url=entity.image_url,
            learning_objectives=entity.learning_objectives,
        )

    @staticmethod
    def basic_info_mapper(row: tuple, modules: list[BasicInfo]) -> CourseBasicInfo:
        return CourseBasicInfo(
            id=row.id,
            title=row.title,
            description=row.description,
            difficulty=row.difficulty,
            tags=row.tags,
            learning_objectives=row.learning_objectives,
            modules=modules,
        )


class LessonTheorySessionMapper(ModelMapper[LessonTheorySession, LessonTheorySessionOrm]):
    @staticmethod
    def from_model(model: LessonTheorySessionOrm) -> LessonTheorySession:
        return LessonTheorySession(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            lesson_id=model.lesson_id,
            user_id=model.user_id,
            completed_at=model.completed_at,
            active_time_seconds=model.active_time_seconds,
            max_scroll_depth_percent=model.max_scroll_depth_percent,
        )

    @staticmethod
    def to_model(entity: LessonTheorySession) -> LessonTheorySessionOrm:
        return LessonTheorySessionOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            lesson_id=entity.lesson_id,
            user_id=entity.user_id,
            completed_at=entity.completed_at,
            active_time_seconds=entity.active_time_seconds,
            max_scroll_depth_percent=entity.max_scroll_depth_percent,
        )


class DocumentMapper(ModelMapper[Document, DocumentOrm]):
    @staticmethod
    def from_model(model: DocumentOrm) -> Document:
        return Document(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            owner_id=model.owner_id,
            parent_node_id=model.parent_node_id,
            node_type=model.node_type,
            title=model.title,
            content=model.content,
        )

    @staticmethod
    def to_model(entity: Document) -> DocumentOrm:
        return DocumentOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            owner_id=entity.owner_id,
            parent_node_id=entity.parent_node_id,
            node_type=entity.node_type,
            title=entity.title,
            content=entity.content,
        )


class PracticeMapper(ModelMapper[Practice, PracticeOrm]):
    @staticmethod
    def from_model(model: PracticeOrm) -> Practice:
        return Practice(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            user_id=model.user_id,
            module_id=model.module_id,
            lesson_id=model.lesson_id,
            status=model.status,
            practice=model.practice,
        )

    @staticmethod
    def to_model(entity: Practice) -> PracticeOrm:
        return PracticeOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            user_id=entity.user_id,
            module_id=entity.module_id,
            lesson_id=entity.lesson_id,
            status=entity.status,
            practice=entity.practice,
        )


class StudentMapper(ModelMapper[Student, StudentOrm]):
    @staticmethod
    def from_model(model: StudentOrm) -> Student:
        return Student(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            course_id=model.course_id,
            user_id=model.user_id,
        )

    @staticmethod
    def to_model(entity: Student) -> StudentOrm:
        return StudentOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            course_id=entity.course_id,
            user_id=entity.user_id,
        )
