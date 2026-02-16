from uuid import UUID

from faststream.redis import RedisBroker

from app.core.entities.course import Course
from app.infra.db.repos import CourseRepository

from ..schemas import CourseGenerate


class GenerateCourseUseCase:
    def __init__(self, repository: CourseRepository, broker: RedisBroker) -> None:
        self.repository = repository
        self.broker = broker

    async def execute(self, user_id: UUID, title: str, prompt: str) -> Course:
        course = Course(creator_id=user_id, title=title, description="")
        await self.repository.create(course)
        await self.broker.publish(
            CourseGenerate(course_id=course.id, prompt=prompt), channel=...
        )
        return course
