__all__ = ("router",)

from aiogram import Router

from .course_creation import router as create_course_router

router = Router()

router.include_router(create_course_router)
