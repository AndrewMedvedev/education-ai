from uuid import UUID, uuid4

from pydantic import BaseModel, Field, PositiveInt


class Teacher(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: PositiveInt
    full_name: str | None = None
    contact_info: str | None = None
