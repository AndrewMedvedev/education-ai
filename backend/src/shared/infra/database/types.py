from typing import Annotated

from datetime import datetime
from uuid import UUID

from sqlalchemy import TEXT, DateTime
from sqlalchemy.orm import mapped_column

type StrUnique = Annotated[str, mapped_column(unique=True)]
type StrNull = Annotated[str | None, mapped_column(nullable=True)]
type UUIDNull = Annotated[UUID | None, mapped_column(nullable=True)]
type TextNull = Annotated[str | None, mapped_column(TEXT, nullable=True)]
type DatatimeTz = Annotated[datetime, mapped_column(DateTime(timezone=True))]
type DatetimeNull = Annotated[
    datetime | None, mapped_column(DateTime(timezone=True), nullable=True),
]
