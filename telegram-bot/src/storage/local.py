import logging

import aiofiles

from ..core import schemas

logger = logging.getLogger(__name__)


async def upload(file: schemas.File) -> None:
    async with aiofiles.open(file.path, mode="wb") as opened_file:
        await opened_file.write(file.data)
    logger.info("File `%s` uploaded successfully", file.path)
