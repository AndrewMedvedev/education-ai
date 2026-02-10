from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.app import templates
from src.core.dependencies import get_db
from src.features.course import repository

router = APIRouter(prefix="/teacher/courses")


@router.get(path="/modules/{module_id}/theory", response_class=HTMLResponse)
async def get_module_content_blocks_page(
        request: Request,
        module_id: UUID,
        session: AsyncSession = Depends(get_db),
):
    module = await repository.get_module(session, module_id)
    if module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="NOT_FOUND"
        )
    return templates.TemplateResponse(
        "teacher/course/content_blocks.html",
        {
            "request": request,
            "content_blocks": [
                content_block.model_dump() for content_block in module.content_blocks
            ],
        }
    )
