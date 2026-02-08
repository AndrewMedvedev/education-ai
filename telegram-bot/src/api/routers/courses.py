from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import session_factory
from src.features.course import repository, schemas

router = APIRouter(prefix="/courses", tags=["🎓 Courses"])


@router.get(
    path="/{course_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.Course,
    summary="Получение курса",
)
async def get_course(
    course_id: UUID,
    session: AsyncSession = Depends(session_factory),
) -> schemas.Course:
    course = await repository.get(session, course_id)
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Course not found by ID {course_id}"
        )
    return course


@router.put(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=schemas.Course,
    summary="Редактирование курса"
)
async def update_course(
        course: schemas.Course, session: AsyncSession = Depends(session_factory)
) -> schemas.Course:
    return await repository.refresh(session, course)


@router.get(
    path="/modules/{module_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.Module,
    summary="Получение модуля курса"
)
async def get_module(
        module_id: UUID,
        session: AsyncSession = Depends(session_factory),
) -> schemas.Module:
    module = await repository.get_module(session, module_id)
    if module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Module not found by ID {module_id}"
        )
    return module
