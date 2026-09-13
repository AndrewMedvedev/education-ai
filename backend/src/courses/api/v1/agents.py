# pyright: reportArgumentType=false

from __future__ import annotations

from typing import Any

import json
from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import TypeAdapter

from src.iam.dependencies import require_permissions
from src.iam.dependencies.identity import CurrentIdentity

from ...agents.schemas import AnyKnowledgeTest, Context, PracticeResult
from ...application.dtos import Chat, EditorChat, MentorChat
from ...dependencies.agents import (
    EditorAgentDep,
    InterviewerAgentDep,
    MentorAgentDep,
    PracticeAgentDep,
    TesterAgentDep,
)
from ...domain.entities import FileUploadAssignment
from ...domain.permissions.courses import COURSE_READ, CREATE, UPDATE
from ...utils.docs_processing import read_upload_with_limit

router = APIRouter(prefix="/agent", tags=["Agents"])


@router.post(
    "/interviewer",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permissions(CREATE.code))],
)
async def chat_with_interviewer(
    request: Chat,
    agent: InterviewerAgentDep,
    identity: CurrentIdentity,
) -> Chat:
    """Обрабатывает HTTP-запрос `chat_with_interviewer` и связывает API с сервисным слоем."""
    result = await agent.call_agent(
        chat_id=request.chat_id,
        context=Context(
            course_id=request.course_id,
            user_id=identity.id,
            prompt=request.content,
        ),
    )

    return Chat(
        chat_id=request.chat_id,
        course_id=request.course_id,
        role="assistant",
        content=result,
    )


@router.post(
    "/editor",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permissions(UPDATE.code))],
)
async def chat_with_editor(
    request: EditorChat,
    agent: EditorAgentDep,
    identity: CurrentIdentity,
) -> Chat:
    """Обрабатывает HTTP-запрос `chat_with_editor` и связывает API с сервисным слоем."""
    result = await agent.call_agent(
        context=Context(
            course_id=request.course_id,
            user_id=identity.id,
            prompt=request.content,
        ),
        chat=request,
    )

    return Chat(
        chat_id=request.chat_id,
        course_id=request.course_id,
        role="assistant",
        content=json.dumps(asdict(result), ensure_ascii=False, default=str),
    )


@router.post(
    "/mentor",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permissions(COURSE_READ.code))],
)
async def chat_with_mentor(
    request: MentorChat,
    agent: MentorAgentDep,
    identity: CurrentIdentity,
) -> Chat:
    """Обрабатывает HTTP-запрос `chat_with_mentor` и связывает API с сервисным слоем."""
    result = await agent.call_agent(
        chat=request,
        context=Context(
            course_id=request.course_id,
            user_id=identity.id,
            prompt=request.content,
        ),
    )
    return Chat(
        chat_id=request.chat_id,
        course_id=request.course_id,
        role="assistant",
        content=result,
    )


@router.post(
    "/test/{module_id}/{lesson_id}",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(COURSE_READ.code))],
)
async def create_test(
    module_id: UUID,
    lesson_id: UUID,
    agent: TesterAgentDep,
    identity: CurrentIdentity,
) -> dict[str, Any]:
    """Обрабатывает HTTP-запрос `chat_with_mentor` и связывает API с сервисным слоем."""
    return await agent.call_agent_creator(
        user_id=identity.id,
        module_id=module_id,
        lesson_id=lesson_id,
    )


@router.post(
    "/check/test/{practice_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permissions(COURSE_READ.code))],
)
async def check_test(
    practice: AnyKnowledgeTest,
    answers: dict[str, str],
    practice_id: UUID,
    agent: TesterAgentDep,
    _identity: CurrentIdentity,
) -> PracticeResult:
    """Обрабатывает HTTP-запрос `chat_with_mentor` и связывает API с сервисным слоем."""
    return await agent.call_agent_checker(
        practice=practice.model_dump(),
        answers=answers,
        practice_id=practice_id,
    )


@router.post(
    "/practice/{module_id}/{lesson_id}",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(COURSE_READ.code))],
)
async def create_practice(
    module_id: UUID,
    lesson_id: UUID,
    agent: PracticeAgentDep,
    identity: CurrentIdentity,
) -> dict[str, Any]:
    """Обрабатывает HTTP-запрос `chat_with_mentor` и связывает API с сервисным слоем."""
    return await agent.call_agent_creator(
        user_id=identity.id,
        module_id=module_id,
        lesson_id=lesson_id,
    )


@router.post(
    "/check/practice/{practice_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permissions(COURSE_READ.code))],
)
async def check_practice(
    practice_id: UUID,
    agent: PracticeAgentDep,
    _identity: CurrentIdentity,
    file: UploadFile = File(...),
    practice: str = Form(),
) -> PracticeResult:
    """Обрабатывает HTTP-запрос `chat_with_mentor` и связывает API с сервисным слоем."""
    practice_obj = TypeAdapter(FileUploadAssignment).validate_json(practice)
    content = await read_upload_with_limit(file)
    return await agent.call_agent_checker(
        file=content,
        practice=asdict(practice_obj),
        practice_id=practice_id,
    )
