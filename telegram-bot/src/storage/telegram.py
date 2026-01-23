import io
import mimetypes

import magic

from ..bot import bot
from ..core.schemas import File


async def download_file(file_id: str) -> File:
    file = await bot.get_file(file_id)
    file_buffer = await bot.download_file(file.file_path, destination=io.BytesIO())
    file_data = file_buffer.getbuffer().tobytes()
    mime_type = magic.Magic(mime=True).from_buffer(file_data)
    extension = mimetypes.guess_extension(mime_type, strict=True)
    return File(
        path=file.file_path,
        size=len(file_data),
        mime_type=mime_type,
        data=file_data
    )
