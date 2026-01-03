from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/courses")


@router.get(path="/create", response_class=HTMLResponse)
async def create_course(request: Request) -> HTMLResponse:
    from ..app import templates  # noqa: PLC0415

    return templates.TemplateResponse("create_course.html", {"request": request})
