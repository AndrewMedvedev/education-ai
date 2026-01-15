from typing import Any, ClassVar, Self

import logging
from collections.abc import Iterable
from contextlib import contextmanager
from uuid import uuid4

import chromadb
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ...settings import CHROMA_PATH
from ...utils import current_datetime

logger = logging.getLogger(__name__)


class ExpertMaterialsSessionRAG:
    """RAG для работы с материалами эксперта в рамках интервью сессии.
    Индекс удаляется после окончания сессии.
    """

    COLLECTIONS_PREFIX: ClassVar[str] = "interview_sessions"

    def __init__(
            self, embeddings: Embeddings, chunk_size: int = 1000, chunk_overlap: int = 50
    ) -> None:
        self._client = chromadb.PersistentClient(path=CHROMA_PATH / self.COLLECTIONS_PREFIX)
        self._active_sessions: dict[int, str] = {}
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len
        )
        self._embeddings = embeddings

    @contextmanager
    def session(self, expert_id: int) -> Iterable[Self]:
        try:
            yield self
        finally:
            self.stop_session(expert_id)
            logger.debug("[Expert %s] Session closed via context manager", expert_id)

    @staticmethod
    def _build_collection_name(expert_id: int) -> str:
        return f"expert_materials_{expert_id}_{current_datetime()}"

    def index_document(
            self, expert_id: int, text: str, metadata: dict[str, Any] | None = None
    ) -> list[str]:
        if not text.strip():
            logger.warning("[Expert %s] Attempted to index empty text", expert_id)
            return []
        collection_name = self._active_sessions.get(expert_id)
        if collection_name is None:
            collection_name = self._build_collection_name(expert_id)
            self._active_sessions[expert_id] = collection_name
            logger.info("[Expert %s] Created new session: `%s`", expert_id, collection_name)
        collection = self._client.get_or_create_collection(collection_name)

        chunks = self._splitter.split_text(text)
        chunks_count = len(chunks)
        ids = [str(uuid4()) for _ in range(chunks_count)]
        vectors = self._embeddings.embed_documents(chunks)
        metadatas = [metadata.copy() for _ in range(chunks_count)]
        collection.add(
            ids=ids,
            documents=chunks,
            embeddings=vectors,
            metadatas=metadatas,
        )
        return ids

    def retrieve_documents(
            self,
            expert_id: int,
            query: str,
            filename: str | None = None,
            search_string: str | None = None,
            n_results: int = 10,
    ) -> list[str]:
        collection_name = self._active_sessions.get(expert_id)
        if collection_name is None:
            logger.warning("[Expert %s] No active session for retrieval", expert_id)
            return []
        collection = self._client.get_collection(collection_name)
        logger.info("[Expert %s] Retrieving for query: '%s...'", expert_id, query[:50])
        params = {}
        query_vector = self._embeddings.embed_query(query)
        params["query_embeddings"] = [query_vector]
        if filename is not None:
            params["where"] = {"filename": filename}
        if search_string is not None:
            params["where_document"] = {"$contains": search_string}
        params["n_results"] = n_results
        result = collection.query(
            **params, include=["documents", "metadatas", "distances"]
        )
        return [
            f"""
            **Document-ID:** {id_}
            **Relevance score:** {round(distance, 2)}
            **Filename:** {metadata.get('filename', '')}
            **Document:**
            {document}
            """
            for id_, document, metadata, distance in zip(
                result["ids"][0],
                result["documents"][0],
                result["metadatas"][0],
                result["distances"][0],
                strict=False
            )
        ]

    def stop_session(self, expert_id: int) -> None:
        collection_name = self._active_sessions.get(expert_id)
        if collection_name is None:
            logger.warning("[Expert %s] No active session found", expert_id)
            return
        self._client.delete_collection(collection_name)
        del self._active_sessions[expert_id]
        logger.info("[Expert %s] Session `%s` deleted", expert_id, collection_name)
