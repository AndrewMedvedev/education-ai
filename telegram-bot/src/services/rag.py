from typing import Any

import logging
from uuid import uuid4

import chromadb
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..settings import CHROMA_PATH

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(
        self,
        embeddings: Embeddings,
        index_prefix: str = "",
        chunk_size: int = 1000,
        chunk_overlap: int = 50,
    ) -> None:
        self._client = chromadb.PersistentClient(path=CHROMA_PATH / index_prefix)
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len
        )
        self._embeddings = embeddings

    def indexing(
            self, index_name: str, text: str, metadata: dict[str, Any] | None = None
    ) -> list[str]:
        if not text.strip():
            logger.warning("[%s] Attempted to index empty text", index_name)
            return []
        collection = self._client.get_or_create_collection(index_name)
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

    def retrieve(
            self,
            index_name: str,
            query: str,
            metadata_filtering: dict[str, Any] | None = None,
            search_string: str | None = None,
            n_results: int = 10,
    ) -> list[str]:
        collection = self._client.get_collection(index_name)
        logger.info("[%s] Retrieving for query: '%s...'", index_name, query[:50])
        params = {}
        query_vector = self._embeddings.embed_query(query)
        params["query_embeddings"] = [query_vector]
        if metadata_filtering is not None:
            params["where"] = metadata_filtering
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
            **Source:** {metadata.get('source', '')}
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

    def delete(self, index_name: str) -> None:
        self._client.delete_collection(index_name)
        logger.info("[%s] successfully deleted", index_name)
