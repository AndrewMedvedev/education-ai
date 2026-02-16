from pydantic import BaseModel, PositiveInt


class CourseCreationCommand(BaseModel):
    """Задача на создание курса с помощью AI агента"""

    user_id: PositiveInt
    interview_with_teacher: str
