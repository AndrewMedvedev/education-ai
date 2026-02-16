from typing import Annotated

from fastapi import Body, Depends, status
from faststream.redis import RedisBroker, fastapi

from src.app.schemas import CourseGenerate, CurrentUser
from src.app.usecases.generate_course import GenerateCourseUseCase
from src.core.entities.course import Course, CourseStatus
from src.infra.ai.agents.course_generator.schemas import GenerationContext
from src.infra.ai.agents.course_generator.workflow import agent
from src.infra.db.repos import CourseRepository
from src.settings import settings

from ...dependencies import get_course_repo, get_current_user

router = fastapi.RedisRouter(
    url=settings.redis.url, prefix="/course-generator", tags=["Course generator"]
)


def get_broker() -> RedisBroker:
    return router.broker


def get_generate_course_uc(
        repository: CourseRepository = Depends(get_course_repo),
        broker: RedisBroker = Depends(get_broker),
) -> GenerateCourseUseCase:
    return GenerateCourseUseCase(repository, broker)


@router.post(
    path="",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=Course,
    summary="Начать генерацию курса",
)
async def generate_course(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
        prompt: str = Body(..., embed=True),
        usecase: GenerateCourseUseCase = Depends(get_generate_course_uc),
) -> Course:
    return await usecase.execute(user_id=current_user.user_id, prompt=prompt)


@router.subscriber("course:generate")
async def handle_course_generation(
        data: CourseGenerate,
        repository: CourseRepository = Depends(get_course_repo)
) -> None:
    course = await repository.update(data.course_id, status=CourseStatus.IN_GENERATION)
    result = await agent.ainvoke({
        "generation_context": GenerationContext(
            course_id=course.id, user_id=course.creator_id, prompt=data.prompt
        )
    })
    await repository.refresh(result["course"])
