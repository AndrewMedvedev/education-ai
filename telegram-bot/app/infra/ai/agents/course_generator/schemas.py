from uuid import UUID

from pydantic import BaseModel, PositiveInt


class TeacherContext(BaseModel):
    """Контекст преподавателя для генерации образовательного курса"""

    user_id: PositiveInt
    comment: str
    tenant_id: UUID
