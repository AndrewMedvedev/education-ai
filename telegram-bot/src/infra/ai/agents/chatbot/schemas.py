from pydantic import BaseModel, PositiveInt

from ..course_generator.schemas import CourseContext


class UserContext(BaseModel):
    """Контекстная информация пользователя"""

    user_id: PositiveInt


class StudentContext(CourseContext, UserContext):
    """Контекстная информация студента для взаимодействия с чат-ботом"""
