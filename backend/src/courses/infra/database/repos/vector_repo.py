from typing import Any

import logging
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastembed.sparse import SparseTextEmbedding
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import AsyncQdrantClient, models

from src.core.retrieval import embed, rerank

logger = logging.getLogger(__name__)


class QdrantRepository:
    """
    Async RAG repository:

    Dense (embeddings) + BM25 + Qdrant + Reranker.
    """

    def __init__(
        self,
        client: AsyncQdrantClient,
        splitter: RecursiveCharacterTextSplitter,
        collection_name: str = "MAIN_COLLECTION",
    ):
        """Инициализирует объект и сохраняет зависимости, необходимые для дальнейшей работы."""
        self.client = client
        self.splitter = splitter
        self.collection_name = collection_name
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")

    async def create(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        document_id: str | None = None,
    ) -> None:
        if not text.strip():
            logger.warning("Attempted to index empty text")
            return

        metadata = dict(metadata or {})

        chunks = self.splitter.split_text(text)
        points = []

        for index, chunk in enumerate(chunks):
            point_id = (
                str(uuid5(NAMESPACE_URL, f"{document_id}:{index}"))
                if document_id is not None
                else str(uuid4())
            )

            dense_vector = await embed(inputs=[chunk])
            sparse = next(iter(self.sparse_model.embed([chunk])))

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector={
                        "dense": dense_vector[0],
                        "bm25": models.SparseVector(
                            indices=sparse.indices.tolist(),
                            values=sparse.values.tolist(),
                        ),
                    },
                    payload={
                        **metadata,
                        "text": chunk,
                        "chunk_index": index,
                    },
                )
            )

        if points:
            await self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )

    async def read(
        self,
        query: str,
        limit: int = 5,
        prefetch_limit: int = 25,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[str]:
        """Hybrid search: Dense + BM25 + RRF + Rerank."""
        dense_query = (await embed(inputs=[query]))[0]
        sparse_query = next(iter(self.sparse_model.embed([query])))

        qdrant_filter = None
        if metadata_filters:
            conditions: list[models.FieldCondition] = []

            for key, value in metadata_filters.items():
                if isinstance(value, list):
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchAny(any=value),
                        )
                    )
                else:
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value),
                        )
                    )

            qdrant_filter = models.Filter(must=conditions)  # type: ignore

        response = await self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(
                    query=dense_query,
                    using="dense",
                    limit=prefetch_limit,
                    filter=qdrant_filter,
                ),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=sparse_query.indices.tolist(),
                        values=sparse_query.values.tolist(),
                    ),
                    using="bm25",
                    limit=prefetch_limit,
                    filter=qdrant_filter,
                ),
            ],
            query=models.FusionQuery(
                fusion=models.Fusion.RRF,
            ),
            limit=prefetch_limit,
            with_payload=True,
        )

        candidates = []
        texts = []

        for p in response.points:
            payload = p.payload or {}
            text = payload.get("text", "")
            candidates.append(
                {
                    "id": p.id,
                    "text": text,
                    "payload": payload,
                }
            )
            texts.append(text)

        if not texts:
            return []

        # rerank возвращает list[dict] с index, relevance_score, document
        # уже отсортирован по relevance_score desc, берём топ limit
        rerank_results = await rerank(query=query, documents=texts, top_n=limit)

        return [
            (
                f"Утверждение: {candidates[r['index']]['payload'].get('claim', '')}\n"
                f"Подтверждение: {candidates[r['index']]['payload'].get('evidence', '')}\n"
                f"Источник: {candidates[r['index']]['payload'].get('source_title', '')}, "
                f"{candidates[r['index']]['payload'].get('source_organization', '')}\n"
                f"URL: {candidates[r['index']]['payload'].get('source_url', '')}\n"
                f"Категория: {candidates[r['index']]['payload'].get('category', '')}\n"
                f"Релевантность запросу: {round(r['relevance_score'], 2)}"
            )
            for r in rerank_results
        ]
