# pyright: reportArgumentType=false


from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.domain.exceptions import NotFoundError

from ...application.dtos import (
    EditLessonSchema,
    LessonSchema,
)
from ...domain.entities import AnyContentBlock, Lesson
from ..repos import LessonRepository, ModuleRepository
from .base_course import BaseCourseService


class LessonService(BaseCourseService):
    def __init__(
        self,
        lesson_repo: LessonRepository,
        module_repo: ModuleRepository,
        session: AsyncSession,
    ) -> None:
        """Инициализирует объект и сохраняет зависимости, необходимые для дальнейшей работы."""
        super().__init__(repo=lesson_repo, session=session)
        self.module_repo = module_repo

    async def create(self, module_id: UUID | None, schema: LessonSchema) -> Lesson:
        """Создаёт урок и инкапсулирует правила этой операции."""
        lesson = await self.repo.create(Lesson(module_id=module_id, **schema.model_dump()))
        await self.session.commit()
        return lesson

    async def assign_module(self, lesson_id: UUID, module_id: UUID) -> None:
        module = await self.module_repo.exists(module_id)
        if not module:
            raise NotFoundError(f"Module with id {module_id} not found")
        lesson = await self.repo.exists(lesson_id)
        if not lesson:
            raise NotFoundError(f"Lesson with id {lesson_id} not found")
        await self.repo.assign_module(lesson_id, module_id)
        await self.session.commit()

    async def read_content_blocks(self, lesson_id: UUID) -> list[AnyContentBlock]:
        lesson_exists = await self.repo.exists(lesson_id)
        if not lesson_exists:
            raise NotFoundError(f"Lesson with id {lesson_id} not found")
        content_blocks = await self.repo.get_content_blocks_by_id(lesson_id)
        if not content_blocks:
            raise NotFoundError(f"Content blocks for lesson with id {lesson_id} not found")
        return content_blocks

    async def edit(self, lesson_id: UUID, schema: EditLessonSchema) -> Lesson:
        """Выполняет действие `edit_lesson`, чтобы поддержать основной сценарий модуля."""
        lesson_exists = await self.repo.exists(lesson_id)
        if not lesson_exists:
            raise NotFoundError(f"Lesson with id {lesson_id} not found")
        lesson = await self.repo.update(uid=lesson_id, **schema.model_dump(exclude_none=True))
        await self.session.commit()
        return lesson

    async def update_content_blocks(
        self,
        lesson_id: UUID,
        content_blocks: list[AnyContentBlock],
    ) -> Lesson:
        """Обновляет контент-блоки, чтобы синхронизировать сохранённое состояние."""
        lesson_exists = await self.repo.exists(lesson_id)
        if not lesson_exists:
            raise NotFoundError(f"Lesson with id {lesson_id} not found")
        lesson: Lesson = await self.repo.update(uid=lesson_id, content_blocks=content_blocks)
        await self.session.commit()
        return lesson

    async def delete(self, lesson_id: UUID) -> None:
        """Выполняет действие `delete_lesson`, чтобы поддержать основной сценарий модуля."""
        lesson_exists = await self.repo.exists(lesson_id)
        if not lesson_exists:
            raise NotFoundError(f"Lesson with id {lesson_id} not found")
        await self.repo.delete(lesson_id)
        await self.session.commit()
