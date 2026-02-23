from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.infra.db.repos import CourseRepository
from src.settings import TEMPLATES_DIR, settings

from ..dependencies import get_course_repo

router = APIRouter(prefix="/students", tags=["🧑🏻‍🎓 Students"])

templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/courses/{course_id}/modules/{module_id}/theory", response_class=HTMLResponse)
async def get_theory_page(
    request: Request,
    course_id: UUID,
    module_id: str,
    repository: CourseRepository = Depends(get_course_repo),
) -> HTMLResponse:
    course = await repository.read(course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return templates.TemplateResponse(
        context={
            "request": request,
            "course": jsonable_encoder(course),
            "moduleId": module_id,
            "baseURL": settings.app.url
        },
        name="student/student.html"
    )
