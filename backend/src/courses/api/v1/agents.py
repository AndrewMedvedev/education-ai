# pyright: reportArgumentType=false

from __future__ import annotations

from typing import Annotated, Any

from dataclasses import asdict
from datetime import timedelta
from uuid import UUID

from ddf.ratelimit.fastapi import rate_limit
from ddf.ratelimit.models import SlidingWindowPolicy
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import TypeAdapter

from src.courses.agents.schemas import AnyKnowledgeTest, Context, GenerationContext, PracticeResult
from src.courses.application.dtos import (
    Chat,
    EditorChat,
    LessonGenerationChat,
    MentorChat,
    ModuleGenerationChat,
)
from src.courses.dependencies.agents import (
    CourseInterviewerAgentDep,
    EditorAgentDep,
    LessonInterviewerAgentDep,
    MentorAgentDep,
    ModuleInterviewerAgentDep,
    PracticeAgentDep,
    TesterAgentDep,
)
from src.courses.dependencies.services import (
    CheckCourseAccessDep,
    CheckModuleAccessDep,
)
from src.courses.domain.permissions.courses import CREATE, READ, UPDATE
from src.courses.domain.vo import FileUploadAssignment
from src.courses.infra import practice_jobs
from src.courses.utils.docs_processing import read_upload_with_limit
from src.iam.dependencies import require_permissions
from src.iam.dependencies.identity import CurrentIdentity

router = APIRouter(prefix="/agent", tags=["Agents"])


async def get_identity_id(
    identity: CurrentIdentity,
) -> str:
    return str(identity.id)


# 2. Политика ограничения
agents_limit = rate_limit(
    name="agents:ai",
    policy=SlidingWindowPolicy(
        limit=10,
        window=timedelta(minutes=10),
    ),
    identity=get_identity_id,
)


@router.post(
    "/course/interviewer",
    summary="Написать AI-интервьюеру",
    description="Передаёт сообщение AI-интервьюеру, который помогает собрать вводные данные для создания курса.",
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(require_permissions(CREATE.code)),
        Depends(agents_limit),
    ],
)
async def chat_with_course_interviewer(
    request: Chat,
    agent: CourseInterviewerAgentDep,
    identity: CurrentIdentity,
) -> Chat:
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
    "/module/interviewer",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(agents_limit)],
)
async def chat_with_module_interviewer(
    request: ModuleGenerationChat,
    agent: ModuleInterviewerAgentDep,
    identity: CurrentIdentity,
    check_access: CheckCourseAccessDep,
) -> ModuleGenerationChat:
    await check_access(
        identity=identity,
        permission=UPDATE,
        uid=request.course_id,
    )
    result = await agent.call_agent(
        chat_id=request.chat_id,
        context=GenerationContext(
            course_id=request.course_id,
            user_id=identity.id,
            prompt=request.content,
            order=request.order,
        ),
    )

    return ModuleGenerationChat(
        chat_id=request.chat_id,
        course_id=request.course_id,
        role="assistant",
        content=result,
        order=request.order,
    )


@router.post(
    "/lesson/interviewer",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(agents_limit)],
)
async def chat_with_lesson_interviewer(
    request: LessonGenerationChat,
    agent: LessonInterviewerAgentDep,
    identity: CurrentIdentity,
    check_access: CheckCourseAccessDep,
) -> LessonGenerationChat:
    await check_access(
        identity=identity,
        permission=UPDATE,
        uid=request.course_id,
    )
    result = await agent.call_agent(
        chat_id=request.chat_id,
        context=GenerationContext(
            course_id=request.course_id,
            user_id=identity.id,
            prompt=request.content,
            module_id=request.module_id,
            order=request.order,
        ),
    )

    return LessonGenerationChat(
        chat_id=request.chat_id,
        course_id=request.course_id,
        role="assistant",
        content=result,
        module_id=request.module_id,
        order=request.order,
    )


@router.post(
    "/editor",
    summary="Написать AI-редактору",
    description="Передаёт сообщение AI-редактору для редактирования материалов курса.",
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(require_permissions(UPDATE.code)),
        Depends(agents_limit),
    ],
)
async def chat_with_editor(
    request: EditorChat,
    agent: EditorAgentDep,
    identity: CurrentIdentity,
    check_access: CheckCourseAccessDep,
) -> Chat:
    await check_access(
        identity=identity,
        permission=UPDATE,
        uid=request.course_id,
    )
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
        content=asdict(result),
    )


@router.post(
    "/mentor",
    summary="Написать AI-наставнику",
    description="Передаёт сообщение AI-наставнику и возвращает его ответ по материалам курса.",
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(require_permissions(READ.code)),
        Depends(agents_limit),
    ],
)
async def chat_with_mentor(
    request: MentorChat,
    agent: MentorAgentDep,
    identity: CurrentIdentity,
    check_access: CheckCourseAccessDep,
) -> Chat:
    await check_access(
        identity=identity,
        permission=READ,
        uid=request.course_id,
    )
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


@router.get(
    "/test-generations/{module_id}/{lesson_id}",
    summary="Состояние генерации теста",
)
async def get_test_generation(
    module_id: UUID,
    lesson_id: UUID,
    agent: TesterAgentDep,
    identity: CurrentIdentity,
    check_access: CheckModuleAccessDep,
) -> dict[str, Any]:
    await check_access(identity=identity, permission=READ, uid=module_id)
    result = await agent.get_pending_test(identity.id, module_id, lesson_id)
    if result["practice_id"] is not None:
        return {"status": "succeeded", **result}
    job = await practice_jobs.read(identity.id, module_id, lesson_id, kind="test")
    if job and job["status"] in ("queued", "running", "failed"):
        return job
    return {"status": "idle"}


@router.post(
    "/test-generations/{module_id}/{lesson_id}",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(agents_limit)],
)
async def start_test_generation(
    module_id: UUID,
    lesson_id: UUID,
    agent: TesterAgentDep,
    identity: CurrentIdentity,
    check_access: CheckModuleAccessDep,
) -> dict[str, Any]:
    await check_access(identity=identity, permission=READ, uid=module_id)
    result = await agent.get_pending_test(identity.id, module_id, lesson_id)
    if result["practice_id"] is not None:
        return {"status": "succeeded", **result}
    job, created = await practice_jobs.begin(identity.id, module_id, lesson_id, kind="test")
    if created:
        from src.courses.infra.tasks import generate_test

        try:
            await generate_test.kiq(
                str(identity.id), str(module_id), str(lesson_id), job["job_id"]
            )
        except Exception as exc:
            await practice_jobs.transition(
                identity.id,
                module_id,
                lesson_id,
                job["job_id"],
                ("queued",),
                "failed",
                practice_jobs.FINISHED_TTL,
                kind="test",
            )
            raise HTTPException(
                status_code=503, detail="Не удалось запустить генерацию теста"
            ) from exc
    return job


@router.post(
    "/tests/{module_id}/{lesson_id}",
    summary="Сгенерировать тест для урока",
    description="Генерирует тест по указанному уроку с учётом контекста модуля и текущего пользователя.",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(agents_limit)],
)
async def create_test(
    module_id: UUID,
    lesson_id: UUID,
    agent: TesterAgentDep,
    identity: CurrentIdentity,
    check_access: CheckModuleAccessDep,
) -> dict[str, Any]:
    await check_access(
        identity=identity,
        permission=READ,
        uid=module_id,
    )

    return await agent.call_agent_creator(
        user_id=identity.id,
        module_id=module_id,
        lesson_id=lesson_id,
    )


@router.post(
    "/check/tests/{practice_id}",
    summary="Проверить ответы на тест",
    description="Проверяет ответы пользователя на сгенерированный тест и возвращает результат проверки.",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(agents_limit)],
)
async def check_test(
    practice: AnyKnowledgeTest,
    answers: dict[str, str],
    practice_id: UUID,
    agent: TesterAgentDep,
    _identity: CurrentIdentity,
) -> PracticeResult:
    return await agent.call_agent_checker(
        practice=practice.model_dump(),
        answers=answers,
        practice_id=practice_id,
    )


@router.get(
    "/practice-generations/{module_id}/{lesson_id}",
    summary="Получить состояние генерации практики",
    dependencies=[
        Depends(require_permissions(READ.code)),
    ],
)
async def get_practice_generation(
    module_id: UUID,
    lesson_id: UUID,
    agent: PracticeAgentDep,
    identity: CurrentIdentity,
    check_access: CheckModuleAccessDep,
) -> dict[str, Any]:
    await check_access(identity=identity, permission=READ, uid=module_id)
    job = await practice_jobs.read(identity.id, module_id, lesson_id)
    result = await agent.get_latest_practice(identity.id, module_id, lesson_id)
    if result["practice_id"] is not None:
        return {"status": "succeeded", **result, **({"job_id": job["job_id"]} if job else {})}
    if job and job["status"] in ("queued", "running", "failed"):
        return job
    return {"status": "idle"}


@router.post(
    "/practice-generations/{module_id}/{lesson_id}",
    summary="Запустить фоновую генерацию практики",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[
        Depends(require_permissions(READ.code)),
        Depends(agents_limit),
    ],
)
async def start_practice_generation(
    module_id: UUID,
    lesson_id: UUID,
    agent: PracticeAgentDep,
    identity: CurrentIdentity,
    check_access: CheckModuleAccessDep,
) -> dict[str, Any]:
    await check_access(identity=identity, permission=READ, uid=module_id)
    result = await agent.get_latest_practice(identity.id, module_id, lesson_id)
    if result["practice_id"] is not None:
        return {"status": "succeeded", **result}
    job, created = await practice_jobs.begin(identity.id, module_id, lesson_id)
    if created:
        from src.courses.infra.tasks import generate_practice

        try:
            await generate_practice.kiq(
                str(identity.id), str(module_id), str(lesson_id), job["job_id"]
            )
        except Exception as exc:
            await practice_jobs.transition(
                identity.id,
                module_id,
                lesson_id,
                job["job_id"],
                ("queued",),
                "failed",
                practice_jobs.FINISHED_TTL,
            )
            raise HTTPException(
                status_code=503, detail="Не удалось запустить генерацию практики"
            ) from exc
    return job


@router.get(
    "/practices/{module_id}/{lesson_id}",
    summary="Получить последнее практическое задание с загрузкой файла",
    dependencies=[
        Depends(require_permissions(READ.code)),
    ],
)
async def get_practice(
    module_id: UUID,
    lesson_id: UUID,
    agent: PracticeAgentDep,
    identity: CurrentIdentity,
    check_access: CheckModuleAccessDep,
) -> dict[str, Any]:
    await check_access(identity=identity, permission=READ, uid=module_id)
    return await agent.get_latest_practice(
        user_id=identity.id,
        module_id=module_id,
        lesson_id=lesson_id,
    )


@router.post(
    "/practices/{module_id}/{lesson_id}",
    summary="Сгенерировать практическое задание",
    description="Генерирует практическое задание по указанному уроку с учётом контекста модуля.",
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_permissions(READ.code)),
        Depends(agents_limit),
    ],
)
async def create_practice(
    module_id: UUID,
    lesson_id: UUID,
    agent: PracticeAgentDep,
    identity: CurrentIdentity,
    check_access: CheckModuleAccessDep,
) -> dict[str, Any]:
    await check_access(
        identity=identity,
        permission=READ,
        uid=module_id,
    )

    return await agent.call_agent_creator(
        user_id=identity.id,
        module_id=module_id,
        lesson_id=lesson_id,
    )


@router.post(
    "/check/practices/{practice_id}",
    summary="Проверить практическое задание",
    description="Принимает файл с выполненным заданием, проверяет его и возвращает результат.",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(agents_limit)],
)
async def check_practice(
    practice_id: UUID,
    agent: PracticeAgentDep,
    _identity: CurrentIdentity,
    file: Annotated[UploadFile, File()],
    practice: Annotated[str, Form()],
) -> PracticeResult:
    practice_obj = TypeAdapter(FileUploadAssignment).validate_json(practice)
    content = await read_upload_with_limit(file)
    return await agent.call_agent_checker(
        file=content,
        practice=asdict(practice_obj),
        practice_id=practice_id,
    )
