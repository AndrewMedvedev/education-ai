from pathlib import Path

import openai
from markitdown import MarkItDown

from .settings import settings


def convert_document_to_md(path: Path) -> str:
    client = openai.OpenAI(
        api_key=settings.yandexcloud.apikey,
        base_url=settings.yandexcloud.base_url,
        project=settings.yandexcloud.folder_id,
    )
    md = MarkItDown(llm_client=client, llm_model=settings.yandexcloud.gemma_3_27b_it)
    result = md.convert(path)
    return result.text_content
