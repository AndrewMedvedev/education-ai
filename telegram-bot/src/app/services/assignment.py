from uuid import UUID

from src.core.entities.course import AnyAssignment, AssignmentType
from src.infra.ai.agents.course_generator.schemas import TeacherContext
from src.infra.ai.agents.course_generator.subagents.practician import call_practice_agent
from src.infra.db.conn import session_factory
from src.infra.db.repos import CourseRepository, ModuleRepository, StudentRepository
from src.utils.formatting import get_assignment_context, get_module_context


async def generate_assignment(
        course_id: UUID,
        module_id: UUID,
        user_id: int,
        assignment_type: AssignmentType,
        prompt: str
) -> AnyAssignment:
    async with session_factory() as session:
        course_repo = CourseRepository(session)
        course = await course_repo.read(course_id)
        module = next((module for module in course.modules if module.id == module_id), None)
        prompt_template = (
            "## Контекст текущего модуля:\n"
            "<MODULE>\n"
            f"{get_module_context(module)}\n"
            "</MODULE>\n\n"
            "## Создай практическое задание учитывая запрос и материал модуля:\n"
            f"**Промпт**: {prompt}"
        )
        return await call_practice_agent(
            assignment_type, prompt_template, context=TeacherContext(
                user_id=user_id, tenant_id=course.tenant_id, comment=""
            )
        )


async def generate_individual_assignment(module_id: UUID, student_id: UUID):
    async with session_factory() as session:
        module_repo = ModuleRepository(session)
        module = await module_repo.read(module_id)
        prompt_template = ()


async def evaluate_submission(submission: ...): ...
