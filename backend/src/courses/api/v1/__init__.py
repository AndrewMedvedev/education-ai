from fastapi import APIRouter

from . import agents, course, documents, lesson, module, student, theory_session

router = APIRouter()

router.include_router(agents.router)
router.include_router(lesson.router)
router.include_router(module.router)
router.include_router(course.router)
router.include_router(student.router)
router.include_router(theory_session.router)
router.include_router(documents.router)
