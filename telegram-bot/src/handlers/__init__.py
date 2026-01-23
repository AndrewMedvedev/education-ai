__all__ = ("router",)

from aiogram import Router

from .start import router as start_router
from .teachers import router as teacher_router

router = Router()

router.include_routers(teacher_router, start_router)
