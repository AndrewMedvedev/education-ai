from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.entities.course import Course, Module
from src.infra.db.repos import CourseRepository

from ..dependencies import get_course_repo

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get(
    path="/{course_id}",
    status_code=status.HTTP_200_OK,
    response_model=Course,
    summary="Получение курса"
)
async def get_course(
        course_id: UUID, repository: CourseRepository = Depends(get_course_repo)
) -> Course:
    course = await repository.read(course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


@router.get(
    path="/modules/{module_id}",
    status_code=status.HTTP_200_OK,
    response_model=Module,
    summary="Получение модуля"
)
async def get_module(
        module_id: UUID, repository: CourseRepository = Depends(get_course_repo)
) -> Module:
    module = await repository.get_module(module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    return module


@router.put(
    path="",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Обновление курса"
)
async def update_course(
        course: Course, repository: CourseRepository = Depends(get_course_repo)
) -> None:
    await repository.refresh(course)
