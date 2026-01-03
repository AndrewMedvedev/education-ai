import logging

import aiofiles

from .core.schemas import File

logger = logging.getLogger(__name__)


async def upload_file(file: File) -> None:
    async with aiofiles.open(file.path, mode="wb") as opened_file:
        await opened_file.write(file.data)
    logger.info("File `%s` uploaded successfully", file.path)
