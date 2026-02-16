from uuid import UUID

from faststream.redis import RedisBroker

from src.core.entities.course import Course
from src.infra.db.repos import CourseRepository

from ..schemas import CourseGenerate


class GenerateCourseUseCase:
    def __init__(self, repository: CourseRepository, broker: RedisBroker) -> None:
        self.repository = repository
        self.broker = broker

    async def execute(self, user_id: UUID, prompt: str) -> Course:
        course = Course(creator_id=user_id)
        await self.repository.create(course)
        await self.broker.publish(
            CourseGenerate(course_id=course.id, prompt=prompt), channel="course:generate"
        )
        return course
