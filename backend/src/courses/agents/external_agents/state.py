from uuid import UUID

from pydantic import BaseModel


class State(BaseModel):
    chat_id: UUID
