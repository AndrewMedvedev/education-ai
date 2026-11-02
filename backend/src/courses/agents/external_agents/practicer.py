from typing import Any

import asyncio
import base64
import json
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from uuid import UUID

from pydantic import RootModel, TypeAdapter

from src.core.others import thread_executor
from src.llm_service import LLMTextService
from src.shared.application.transaction import Transaction
from src.shared.domain.exceptions import NotFoundError
from src.shared.utils.time import current_datetime

from ...application.repos import LessonRepository, PracticeRepository
from ...domain.entities import Practice
from ...domain.enums import PracticeStatus
from ...domain.events import LessonProgressUpdate, LessonProgressUpdated
from ...domain.vo import FileUploadAssignment
from ...infra.services.client import SrvCourseClient
from ..course_generator.subagents.prompts import ASSIGNMENT_CREATOR_SYSTEM_PROMPT
from ..prompts import ASSIGNMENT_PROMPT, PRACTICE_FILE_CHECKER_PROMPT
from ..schemas import PracticeResult

EXAMPLE_PATH = Path(__file__).resolve().parents[4] / "praktika_modul_7.md"


@lru_cache(maxsize=1)
def load_assignment_example() -> str:
    """Загружает обязательный образец практической работы."""
    markdown = EXAMPLE_PATH.read_text(encoding="utf-8-sig").strip()

    if not markdown:
        raise ValueError(f"Образец практической работы пуст: {EXAMPLE_PATH}")

    return markdown


async def async_load_assignment_example() -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(thread_executor, load_assignment_example)


class PracticerAgent:
    def __init__(
        self,
        practice_repo: PracticeRepository,
        lesson_repo: LessonRepository,
        transaction: Transaction,
        client: SrvCourseClient,
    ) -> None:
        """Инициализирует объект и сохраняет зависимости, необходимые для дальнейшей работы."""
        self._client = client
        self.practice_repo = practice_repo
        self.lesson_repo = lesson_repo
        self.transaction = transaction

    async def validate_lesson(self, module_id: UUID, lesson_id: UUID) -> Any:
        lesson = await self.lesson_repo.read(lesson_id)
        if lesson is None or lesson.module_id != module_id:
            raise NotFoundError(message="Урок не найден в указанном модуле")
        return lesson

    @staticmethod
    def practice_response(practice: Practice | None) -> dict[str, Any]:
        if practice is None:
            return {"practice": None, "practice_id": None, "result": None}
        payload = practice.practice
        if isinstance(payload, list):
            assignment = payload[0]
            result = None
        else:
            # The existing checker stores the assignment alongside its latest result.
            assignment = payload["practice"]
            result = PracticeResult.model_validate(payload).model_dump()
        return {"practice": assignment, "practice_id": practice.id, "result": result}

    async def get_latest_practice(
        self,
        user_id: UUID,
        module_id: UUID,
        lesson_id: UUID,
    ) -> dict[str, Any]:
        await self.validate_lesson(module_id, lesson_id)
        practice = await self.practice_repo.read_latest_file_upload(user_id, module_id, lesson_id)
        return self.practice_response(practice)

    async def call_agent_creator(
        self,
        user_id: UUID,
        module_id: UUID,
        lesson_id: UUID,
    ) -> dict[str, Any]:
        # Keep request dependencies (especially the DB session) alive until commit,
        # even when the request task is cancelled after a browser disconnect.
        task = asyncio.create_task(self._create_or_reuse(user_id, module_id, lesson_id))
        cancelled = False
        while True:
            try:
                response = await asyncio.shield(task)
                break
            except asyncio.CancelledError:
                if task.cancelled():
                    raise
                cancelled = True
        if cancelled:
            raise asyncio.CancelledError
        return response

    async def create_in_background(
        self, user_id: UUID, module_id: UUID, lesson_id: UUID,
    ) -> dict[str, Any]:
        # Worker owns its session; cancellation must stop the operation.
        return await self._create_or_reuse(user_id, module_id, lesson_id)

    async def _create_or_reuse(
        self,
        user_id: UUID,
        module_id: UUID,
        lesson_id: UUID,
    ) -> dict[str, Any]:
        lesson = await self.validate_lesson(module_id, lesson_id)
        await self.practice_repo.lock_file_upload(user_id, module_id, lesson_id)
        existing = await self.practice_repo.read_latest_file_upload(user_id, module_id, lesson_id)
        if existing is not None:
            await self.transaction()
            return self.practice_response(existing)

        example = await async_load_assignment_example()

        messages = [
            {
                "role": "user",
                "content": ASSIGNMENT_PROMPT,
            },
            {
                "role": "user",
                "content": (
                    "ОБЯЗАТЕЛЬНЫЙ ОБРАЗЕЦ ПРАКТИЧЕСКОЙ РАБОТЫ\n"
                    "Источник: praktika_modul_7.md.\n"
                    "Используй документ как эталон структуры, "
                    "методической глубины и детализации.\n"
                    "Не переноси механически его тему, номер модуля, "
                    "автора и примеры результатов в новую работу.\n"
                    "Примеры выполненной работы являются иллюстрациями, "
                    "а не фактическими результатами студента.\n\n"
                    "<assignment_example>\n"
                    f"{example}\n"
                    "</assignment_example>"
                ),
            },
            {
                "role": "user",
                "content": (
                    "ТЕОРИЯ ТЕКУЩЕГО УРОКА\n"
                    "Определяет тему, содержание и сложность "
                    "создаваемой практической работы:\n\n"
                    f"{lesson.content_blocks}"
                ),
            },
        ]
        practices = await self.practice_repo.read_by_module(user_id=user_id, module_id=module_id)
        if practices is not None:
            messages.append(
                {
                    "role": "user",
                    "content": f"Практики студента\n{json.dumps(practices, ensure_ascii=False, indent=2)}",
                }
            )
        agent = LLMTextService(
            client=self._client,
            system_prompt=ASSIGNMENT_CREATOR_SYSTEM_PROMPT,
            request_timeout=1200,
        )
        result = await agent.invoke(messages=messages, schema=RootModel[FileUploadAssignment])
        practice = TypeAdapter(FileUploadAssignment).validate_python(result.output)
        created = await self.practice_repo.create(
            Practice(
                user_id=user_id,
                module_id=module_id,
                lesson_id=lesson_id,
                practice=[asdict(practice)],
            ),
        )
        await self.transaction(created)
        return {"practice": practice, "practice_id": created.id}

    async def call_agent_checker(
        self,
        practice: dict[str, Any],
        file: bytes,
        practice_id: UUID,
    ) -> PracticeResult:
        """Проверяет практику, сохраняет результат и публикует событие при успешном прохождении."""
        if not await self.practice_repo.exists(practice_id):
            raise NotFoundError("Practice was not found")

        file_str = base64.b64encode(file).decode("utf-8")
        agent = LLMTextService(
            client=self._client,
            system_prompt=PRACTICE_FILE_CHECKER_PROMPT,
        )
        result = await agent.invoke(
            messages=[
                {"role": "user", "content": json.dumps(practice, ensure_ascii=False, indent=2)},
                {"role": "user", "content": f"Результат выполнения практики\n{file_str}"},
            ],
            schema=PracticeResult,
        )
        response = PracticeResult.model_validate(result.output)
        if response.is_passed:
            practice_entity = await self.practice_repo.update(
                uid=practice_id,
                status=PracticeStatus.COMPLETED,
                practice={"practice": practice, **response.model_dump()},
            )
            practice_entity.register_event(
                LessonProgressUpdated(
                    user_id=practice_entity.user_id,
                    lesson_id=practice_entity.lesson_id,
                    progress=LessonProgressUpdate(practice_completed_at=current_datetime()),
                )
            )
        else:
            practice_entity = await self.practice_repo.update(
                uid=practice_id,
                status=PracticeStatus.FAILED,
                practice={"practice": practice, **response.model_dump()},
            )
        await self.transaction(practice_entity)
        return response
