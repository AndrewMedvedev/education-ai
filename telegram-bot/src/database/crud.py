from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy import insert

from .base import Base, sessionmaker

SchemaT = TypeVar("SchemaT", bound=BaseModel)
ModelT = TypeVar("ModelT", bound=Base)


async def create[SchemaT: BaseModel, ModelT: Base](
        schema: SchemaT, *, model_class: type[ModelT]
) -> None:
    async with sessionmaker() as session:
        stmt = insert(model_class).values(**schema.model_dump())
        await session.execute(stmt)
        await session.commit()
