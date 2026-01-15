import io
from datetime import datetime

from markitdown import MarkItDown

from .settings import TIMEZONE


def current_datetime() -> datetime:
    """Получение текущего времени в выбранном часовом поясе"""

    return datetime.now(TIMEZONE)


def convert_document_to_markdown(file_data: bytes, file_extension: str) -> str:
    """Конвертирует контент документа (.pptx, .pdf, .docx, .xlsx) в Markdown текст.

    :param file_data: Байты исходного документа.
    :param file_extension: Расширение документа, например: .pdf, .docx, .xlsx
    :returns: Markdown текст.
    """

    md = MarkItDown()
    result = md.convert_stream(io.BytesIO(file_data), file_extension=file_extension)
    return result.text_content
