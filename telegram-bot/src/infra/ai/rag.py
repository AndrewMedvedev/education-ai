from typing import Any

import asyncio
import logging
import time
from collections.abc import Callable
from itertools import starmap
from uuid import uuid4

import aiohttp
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.settings import CHROMA_PATH, settings

logger = logging.getLogger(__name__)

client = chromadb.PersistentClient(CHROMA_PATH)
splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=50, length_function=len)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
)
async def get_embeddings(texts: list[str], batch_size: int = 10) -> list[list[float]]:
    """Векторизация текста.

    :param texts: Тексты, которые нужно векторизовать.
    :param batch_size: Количество текста векторизуемого за один запрос.
    :returns: Массив ембедингов.
    """

    logger.info(
        "POST: `%s` for get embeddings", f"{settings.huggingface.space_url}/embeddings"
    )
    timeout = aiohttp.ClientTimeout(total=120 * 5)
    headers = {"Content-Type": "application/json"}
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        async with aiohttp.ClientSession(
                base_url=settings.huggingface.space_url, timeout=timeout
        ) as session, session.post(
            url="/embeddings", json={"texts": batch_texts}, headers=headers
        ) as response:
            response.raise_for_status()
            data = await response.json()
            if data.get("embeddings") is None:
                raise ValueError("Missing embeddings values in JSON response!")
            batch_embeddings = data["embeddings"]
            embeddings.extend(batch_embeddings)
    return embeddings


async def index_document(
        index_name: str, text: str, metadata: dict[str, Any] | None = None
) -> list[str]:
    """Индексация и добавление документа в семантический индекс.

    :param index_name: Индекс в который нужно добавить документ.
    :param text: Текст документа.
    :param metadata: Мета-информация документа.
    :returns: Идентификаторы чанков в индексе.
    """

    if not text.strip():
        logger.warning("Attempted to index empty text!")
        return []
    start_time = time.monotonic()
    logger.info("Starting index document text, length %s characters", len(text))
    collection = client.get_or_create_collection(index_name)
    chunks = splitter.split_text(text)
    ids = [str(uuid4()) for _ in range(len(chunks))]
    embeddings = await get_embeddings(chunks)
    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=[metadata.copy() for _ in range(len(chunks))],
    )
    logger.info(
        "Finished indexing text, time %s seconds", round(time.monotonic() - start_time, 2))
    return ids


def _format_result_default(
        document: str, metadata: dict[str, Any], distance: float | None = None
) -> str:
    """Дефолтная функция для форматирования результата поиска релевантных документов"""

    return (
        f"**Relevance score:** {round(distance, 2)}\n"
        f"**Source:** {metadata.get('source', '')}\n"
        f"**Category:** {metadata.get('category', '')}\n"
        "**Document:**\n"
        f"{document}"
    )


async def retrieve_documents(
        index_name: str,
        query: str,
        metadata_filter: dict[str, Any] | None = None,
        search_string: str | None = None,
        n_results: int = 10,
        format_result_func: Callable[
            [str, dict[str, Any], float | None], str
        ] = _format_result_default,
) -> list[str]:
    """Извлечение релевантных документов из семантического индекса.

    :param index_name: Индекс к которому нужно сделать запрос.
    :param query: Запрос для поиска.
    :param metadata_filter: Метаданные для фильтрации, пример: `{"source": "my_file.pdf"}`.
    :param search_string: Подстрока для поиска.
    :param n_results: Количество извлекаемых документов.
    :param format_result_func: Функция для форматирования результата к строке (тексту).
    """

    collection = client.get_or_create_collection(index_name)
    logger.info("Retrieving for query: '%s...'", query[:50])
    params = {}
    embeddings = await get_embeddings([query])
    params["query_embeddings"] = embeddings
    if metadata_filter is not None:
        params["where"] = metadata_filter
    if search_string is not None:
        params["where_document"] = {"$contains": search_string}
    params["n_results"] = n_results
    result = collection.query(
        **params, include=["documents", "metadatas", "distances"]
    )
    return list(
        starmap(
            format_result_func,
            zip(
                result["documents"][0],
                result["metadatas"][0],
                result["distances"][0],
                strict=False
            )
        )
    )
