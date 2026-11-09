from typing import Any

import asyncio
import json
import secrets
from uuid import UUID

from pydantic import TypeAdapter

from src.llm_service import LLMTextService
from src.shared.application.transaction import Transaction
from src.shared.domain.exceptions import NotFoundError
from src.shared.utils.time import current_datetime

from ...application.repos import LessonRepository, PracticeRepository
from ...domain.entities import Practice
from ...domain.enums import PracticeStatus
from ...domain.events import LessonProgressUpdate, LessonProgressUpdated
from ...domain.vo import TestType
from ...infra.services.client import SrvCourseClient
from ..prompts import ASSIGNMENT_PROMPT, KNOWLEDGE_CONFIG, TEST_CHECKER_PROMPT
from ..schemas import AnyKnowledgeTest, PracticeResult


class TesterAgent:
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

    async def call_agent_creator(
        self,
        user_id: UUID,
        module_id: UUID,
        lesson_id: UUID,
    ) -> dict[str, Any]:
        """Сохраняет результат до закрытия зависимостей даже при отмене запроса."""
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

    async def get_pending_test(
        self,
        user_id: UUID,
        module_id: UUID,
        lesson_id: UUID,
    ) -> dict[str, Any]:
        lesson = await self.lesson_repo.read(lesson_id)
        if lesson is None or lesson.module_id != module_id:
            raise NotFoundError(message="Урок не найден в указанном модуле")
        test = await self.practice_repo.read_latest_knowledge_test(user_id, module_id, lesson_id)
        if test is None or test.status != PracticeStatus.NOT_STARTED:
            return {"practice": None, "practice_id": None, "result": None}
        return {"practice": test.practice[0], "practice_id": test.id, "result": None}

    async def create_in_background(
        self,
        user_id: UUID,
        module_id: UUID,
        lesson_id: UUID,
    ) -> dict[str, Any]:
        return await self._create_or_reuse(user_id, module_id, lesson_id)

    async def _create_or_reuse(
        self, user_id: UUID, module_id: UUID, lesson_id: UUID
    ) -> dict[str, Any]:
        lesson = await self.lesson_repo.read(lesson_id)
        if lesson is None or lesson.module_id != module_id:
            raise NotFoundError(message="Урок не найден в указанном модуле")
        await self.practice_repo.lock_knowledge_test(user_id, module_id, lesson_id)
        existing = await self.practice_repo.read_latest_knowledge_test(
            user_id, module_id, lesson_id
        )
        if existing is not None and existing.status == PracticeStatus.NOT_STARTED:
            await self.transaction()
            return {"practice": existing.practice[0], "practice_id": existing.id}

        random_type = secrets.choice(list(TestType))
        config = KNOWLEDGE_CONFIG.get(random_type, {})
        messages = [
            {"role": "user", "content": ASSIGNMENT_PROMPT},
            {"role": "user", "content": f"Теория урока\n{lesson.content_blocks}"},
        ]
        practices = await self.practice_repo.read_by_module(user_id=user_id, module_id=module_id)
        if practices is not None:
            messages.append(
                {
                    "role": "user",
                    "content": f"Практика студента:\n{json.dumps(practices, ensure_ascii=False, indent=2)}",
                }
            )
        agent = LLMTextService(
            client=self._client,
            system_prompt=config.get("system_prompt", ""),
            request_timeout=1200,
        )
        response_format: AnyKnowledgeTest = config.get("response_format")  # pyright: ignore[reportAssignmentType]
        result = await agent.invoke(messages=messages, schema=response_format)
        practice: AnyKnowledgeTest = TypeAdapter(response_format).validate_python(result.output)
        created = await self.practice_repo.create(
            Practice(
                user_id=user_id,
                module_id=module_id,
                lesson_id=lesson_id,
                practice=[practice.model_dump()],
            ),
        )
        await self.transaction(created)
        return {"practice": practice, "practice_id": created.id}

    async def call_agent_checker(
        self,
        practice: dict[str, Any],
        answers: dict[str, str],
        practice_id: UUID,
    ) -> PracticeResult:
        """Проверяет тест, сохраняет результат и публикует событие при успешном прохождении."""
        if not await self.practice_repo.exists(practice_id):
            raise NotFoundError("Practice was not found")

        agent = LLMTextService(
            client=self._client,
            system_prompt=TEST_CHECKER_PROMPT,
        )
        result = await agent.invoke(
            messages=[
                {
                    "role": "user",
                    "content": f"Практика студента:\n{json.dumps(practice, ensure_ascii=False, indent=2)}",
                },
                {
                    "role": "user",
                    "content": f"Ответы студента:\n{json.dumps(answers, ensure_ascii=False, indent=2)}",
                },
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
                    progress=LessonProgressUpdate(test_completed_at=current_datetime()),
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
