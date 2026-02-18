from uuid import UUID

from pydantic import BaseModel


class CourseGenerate(BaseModel):
    """DTO для генерации курса"""

    course_id: UUID
    prompt: str
