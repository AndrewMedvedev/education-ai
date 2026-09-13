# ruff: file-ignore[line-too-long]

from typing import Any

import base64
import json
from dataclasses import asdict
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from src.llm_service import LLMTextService
from src.shared.domain.exceptions import NotFoundError
from src.shared.infra.services import SrvBaseClient

from ...application.repos import LessonRepository, PracticeRepository
from ...domain.entities import FileUploadAssignment, Practice
from ...domain.vo import PracticeStatus
from ..course_generator.subagents.prompts import FILE_UPLOAD_PROMPT
from ..prompts import ASSIGNMENT_PROMPT, PRACTICE_FILE_CHECKER_PROMPT
from ..schemas import PracticeResult


class PracticerAgent:
    def __init__(
        self,
        session: AsyncSession,
        practice_repo: PracticeRepository,
        lesson_repo: LessonRepository,
        client: SrvBaseClient,
    ) -> None:
        """Инициализирует объект и сохраняет зависимости, необходимые для дальнейшей работы."""
        self._client = client
        self.session = session
        self.practice_repo = practice_repo
        self.lesson_repo = lesson_repo

    async def call_agent_creator(
        self,
        user_id: UUID,
        module_id: UUID,
        lesson_id: UUID,
    ) -> dict[str, Any]:
        """Создает практическое задание для студента на основе теории урока и его предыдущих практик."""
        lesson = await self.lesson_repo.read(lesson_id)
        if lesson is None:
            raise NotFoundError(message="Урок не найден")
        messages = [
            {"role": "user", "content": ASSIGNMENT_PROMPT},
            {"role": "user", "content": f"Теория урока\n{lesson.content_blocks}"},
        ]
        practices = await self.practice_repo.read_by_module(user_id=user_id, module_id=module_id)
        if practices is not None:
            messages.append({
                "role": "user",
                "content": f"Практики студента\n{json.dumps(practices, ensure_ascii=False, indent=2)}",
            })
        agent = LLMTextService(
            client=self._client,
            system_prompt=FILE_UPLOAD_PROMPT,
        )
        result = await agent.invoke(messages=messages, schema=FileUploadAssignment)
        practice = TypeAdapter(FileUploadAssignment).validate_python(result.output)
        created = await self.practice_repo.create(
            Practice(
                user_id=user_id,
                module_id=module_id,
                lesson_id=lesson_id,
                practice=[asdict(practice)],
            ),
        )
        await self.session.commit()
        return {"practice": practice, "practice_id": created.id}

    async def call_agent_checker(
        self,
        practice: dict[str, Any],
        file: bytes,
        practice_id: UUID,
    ) -> PracticeResult:
        """Оставляет точку расширения для будущей проверки практических заданий."""
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
            await self.practice_repo.update(
                uid=practice_id,
                status=PracticeStatus.COMPLETED,
                practice={"practice": practice, **response.model_dump()},
            )
        else:
            await self.practice_repo.update(
                uid=practice_id,
                status=PracticeStatus.FAILED,
                practice={"practice": practice, **response.model_dump()},
            )
        await self.session.commit()
        return response
