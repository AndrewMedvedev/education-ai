from pydantic import BaseModel


class UnreadCountOut(BaseModel):
    unread_count: int | None = 0
