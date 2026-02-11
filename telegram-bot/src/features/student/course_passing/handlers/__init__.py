__all__ = ["router"]

from aiogram import Router

from .list_courses import router as list_courses_router
from .my_progress import router as my_progress_router
from .studying import router as studying_router

router = Router()

router.include_routers(list_courses_router, my_progress_router, studying_router)
