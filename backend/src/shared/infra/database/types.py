from typing import Annotated

import uuid
from datetime import datetime

from sqlalchemy import TEXT, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column

type StrUnique = Annotated[str, mapped_column(unique=True)]
type StrNull = Annotated[str | None, mapped_column(nullable=True)]

type UuidNull = Annotated[
    uuid.UUID | None, mapped_column(UUID[uuid.UUID](as_uuid=True), nullable=True)
]
type TextNull = Annotated[str | None, mapped_column(TEXT, nullable=True)]
type DatetimeTz = Annotated[datetime, mapped_column(DateTime(timezone=True))]
type DatetimeNull = Annotated[
    datetime | None,
    mapped_column(DateTime(timezone=True), nullable=True),
]
