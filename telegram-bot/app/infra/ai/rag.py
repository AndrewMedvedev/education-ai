from typing import Any

import logging
from uuid import uuid4

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

from app.settings import CHROMA_PATH

INDEX_NAME = "main-index"

logger = logging.getLogger(__name__)

hf_model = SentenceTransformer("deepvk/USER-bge-m3")
client = chromadb.PersistentClient(CHROMA_PATH)
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1024, chunk_overlap=50, length_function=len
)


def indexing(text: str, metadata: dict[str, Any] | None = None) -> list[str]:
    """Индексация и добавление документа в семантический индекс.

    :param text: Текст документа.
    :param metadata: Мета-информация документа.
    :returns: Идентификаторы чанков в индексе.
    """

    if not text.strip():
        logger.warning("Attempted to index empty text!")
        return []
    collection = client.get_or_create_collection(INDEX_NAME)
    chunks = splitter.split_text(text)
    ids = [str(uuid4()) for _ in range(len(chunks))]
    embeddings = hf_model.encode_document(chunks, normalize_embeddings=False)
    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings.tolist(),
        metadatas=[metadata.copy() for _ in range(len(chunks))],
    )
    return ids


def retrieve(
        query: str,
        metadata_filter: dict[str, Any] | None = None,
        search_string: str | None = None,
        n_results: int = 10,
) -> list[str]:
    """Извлечение релевантных документов из семантического индекса.

    :param query: Запрос для поиска.
    :param metadata_filter: Метаданные для фильтрации, пример: `{"source": "my_file.pdf"}`.
    :param search_string: Подстрока для поиска.
    :param n_results: Количество извлекаемых документов.
    """

    collection = client.get_collection(INDEX_NAME)
    logger.info("Retrieving for query: '%s...'", query[:50])
    params = {}
    embedding = hf_model.encode_query(query, normalize_embeddings=False)
    params["query_embeddings"] = [embedding.tolist()]
    if metadata_filter is not None:
        params["where"] = metadata_filter
    if search_string is not None:
        params["where_document"] = {"$contains": search_string}
    params["n_results"] = n_results
    result = collection.query(
        **params, include=["documents", "metadatas", "distances"]
    )
    return [
        (
            f"**Relevance score:** {round(distance, 2)}\n"
            f"**Source:** {metadata.get('source', '')}\n"
            "**Document:**\n"
            f"{document}"
        )
        for document, metadata, distance in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0], strict=False
        )
    ]
