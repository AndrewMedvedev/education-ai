from fastapi import Body, Depends, status
from faststream.redis import RedisBroker, fastapi

from app.app.schemas import CourseGenerate
from app.app.usecases.generate_course import GenerateCourseUseCase
from app.core.entities.course import Course
from app.infra.db.repos import CourseRepository
from app.settings import settings

from ...dependencies import get_course_repo

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
    response_model=...,
    summary="Начать генерацию курса",
)
async def generate_course(
        title: str = Body(..., embed=True),
        prompt: str = Body(..., embed=True),
        usecase: GenerateCourseUseCase = Depends(get_generate_course_uc),
) -> Course:
    return await usecase.execute(user_id=..., title=title, prompt=prompt)


@router.subscriber("course:generate")
async def handle_course_generation(dto: CourseGenerate) -> None:
    ...
