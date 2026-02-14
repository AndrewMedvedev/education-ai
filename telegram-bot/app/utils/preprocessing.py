import io

from markitdown import MarkItDown


def convert_document_to_md(content: bytes, file_extension: str) -> str:
    """Конвертирует документ (.pptx, .pdf, .docx, .xlsx) в Markdown текст.

    :param content: Байты исходного документа.
    :param file_extension: Расширение документа, например: .pdf, .docx, .xlsx
    :returns: Markdown текст.
    """

    md = MarkItDown()
    result = md.convert_stream(io.BytesIO(content), file_extension=file_extension)
    return result.text_content
