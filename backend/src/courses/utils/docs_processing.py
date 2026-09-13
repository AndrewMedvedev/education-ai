# document_hierarchy_pipeline.py
import asyncio
import contextlib
import io
import re
from dataclasses import dataclass, field
from uuid import UUID

from fastapi import UploadFile
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter
from markitdown import MarkItDown

from src.core.others import thread_executor

from ..domain.exceptions import PayloadTooLargeError

MAX_FILE_SIZE = 30 * 1024 * 1024  # 30 МБ
CHUNK_SIZE = 1024 * 1024  # 1 МБ — размер порции при потоковом чтении


DEFAULT_HEADERS: list[tuple[str, str]] = [
    ("#", "H1"),
    ("##", "H2"),
    ("###", "H3"),
    ("####", "H4"),
]


MEDIA_PATTERN = re.compile(r"!\[(.*?)\]\(media://([0-9a-fA-F-]+)\)")
_HEADING_ONLY_RE = re.compile(r"^#{1,6}\s*$")

_markitdown: MarkItDown = MarkItDown()


@dataclass(frozen=True)
class TextChunk:
    """Хранит данные `TextChunk`, чтобы явно описать форму объекта в этом модуле."""

    order: int
    content: str
    context_heading: list[str] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class MediaChunk:
    """Хранит данные `MediaChunk`, чтобы явно описать форму объекта в этом модуле."""

    attachment_id: UUID
    alt_text: str | None = None
    start_char: int
    end_char: int


def convert_document_to_md(file: bytes, file_extension: str) -> str:
    """Выполняет действие `convert_document_to_md`, чтобы поддержать основной сценарий модуля."""
    return _markitdown.convert_stream(io.BytesIO(file), file_extension=file_extension).markdown


async def convert_document_to_md_async(file: bytes, file_extension: str) -> str:
    # convert_stream блокирует event loop — выносим в отдельный поток
    """Выполняет действие `convert_document_to_md_async`, чтобы поддержать основной сценарий модуля."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        thread_executor,
        convert_document_to_md,
        file,
        file_extension,
    )


def extract_media(md_content: str) -> list["MediaChunk"]:
    """Выполняет действие `extract_media`, чтобы поддержать основной сценарий модуля."""
    media = []
    for match in MEDIA_PATTERN.finditer(md_content):
        alt, attachment_id = match.groups()
        with contextlib.suppress(ValueError):
            media.append(
                MediaChunk(
                    attachment_id=UUID(attachment_id),
                    alt_text=alt.strip(),
                    start_char=match.start(),
                    end_char=match.end(),
                )
            )
    return media


def remove_media_syntax(md_content: str, chunks: list["MediaChunk"]) -> str:
    # Один проход + join() вместо слайс-присваивания в list (было O(n*m), стало O(n))
    """Выполняет действие `remove_media_syntax`, чтобы поддержать основной сценарий модуля."""
    if not chunks:
        return md_content
    parts, cursor = [], 0
    for chunk in sorted(chunks, key=lambda c: c.start_char):
        start = max(chunk.start_char, cursor)
        if start >= chunk.end_char:
            continue
        parts.extend((md_content[cursor:start], chunk.alt_text or ""))
        cursor = chunk.end_char
    parts.append(md_content[cursor:])
    return "".join(parts)


def get_header_order(headers_to_split_on: list[tuple[str, str]] | None = None) -> list[str]:
    """Получает header order, чтобы вызывающий код работал через единый интерфейс."""
    return [name for _, name in (headers_to_split_on or DEFAULT_HEADERS)]


def get_heading_chain(doc: Document, header_order: list[str]) -> list[str]:
    """Получает heading chain, чтобы вызывающий код работал через единый интерфейс."""
    return [v.strip() for k in header_order if (v := doc.metadata.get(k)) and v.strip()]


def is_heading_only(content: str) -> bool:
    # Заголовок без текста после него ("##" и т.п.) — мусорный чанк
    """Выполняет действие `is_heading_only`, чтобы поддержать основной сценарий модуля."""
    return bool(_HEADING_ONLY_RE.fullmatch(content.strip()))


def split_markdown(md_content: str, headers_to_split_on=None) -> list[Document]:
    """Выполняет действие `split_markdown`, чтобы поддержать основной сценарий модуля."""
    if not md_content.strip():
        return []
    headers = headers_to_split_on or DEFAULT_HEADERS
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers, strip_headers=False)
    cleaned = remove_media_syntax(md_content, extract_media(md_content))
    docs = splitter.split_text(cleaned)
    return [d for d in docs if not is_heading_only(d.page_content)]


async def document_pipeline(file: bytes, file_extension: str) -> list[Document]:
    """Выполняет действие `document_pipeline`, чтобы поддержать основной сценарий модуля."""
    md = await convert_document_to_md_async(file=file, file_extension=file_extension)
    return split_markdown(md)


async def read_upload_with_limit(file: UploadFile) -> bytes:
    """
    Читает UploadFile порциями по CHUNK_SIZE, чтобы:
    1) не доверять заголовку Content-Length (его можно подделать/не прислать),
    2) оборвать чтение сразу при превышении лимита, не дожидаясь докачки
       оставшихся данных клиентом.
    """
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(CHUNK_SIZE):
        total += len(chunk)
        if total > MAX_FILE_SIZE:
            raise PayloadTooLargeError
        chunks.append(chunk)
    return b"".join(chunks)
