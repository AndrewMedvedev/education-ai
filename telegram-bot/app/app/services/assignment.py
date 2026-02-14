from uuid import UUID

from app.core.entities.course import AnyAssignment


async def generate_individual_assignment(
        student_id: UUID, module_id: UUID, progress: ...
) -> AnyAssignment: ...


async def evaluate_submission(): ...
