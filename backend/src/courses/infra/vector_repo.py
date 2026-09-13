from typing import Any

import logging
import time
from uuid import uuid4

from fastembed.sparse import SparseTextEmbedding
from qdrant_client import AsyncQdrantClient, models

from src.core.retrieval import embed, rerank

from ..dependencies.base import splitter

logger = logging.getLogger(__name__)


class VectorRepository:
    """
    Async RAG repository:

    Dense (embeddings) + BM25 + Qdrant + Reranker.
    """

    def __init__(
        self,
        client: AsyncQdrantClient,
        collection_name: str = "MAIN_COLLECTION",
    ):
        """Инициализирует объект и сохраняет зависимости, необходимые для дальнейшей работы."""
        self.client = client
        self.collection_name = collection_name
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")

    async def index_document(self, text: str, metadata: dict[str, Any] | None = None) -> None:
        """Асинхронная индексация"""

        if not text.strip():
            logger.warning("Attempted to index empty text!")
            return

        start_time = time.monotonic()
        logger.info("Starting index document text, length %s characters", len(text))
        chunks = splitter.split_text(text)
        points = []
        for chunk in chunks:
            dense_vector = await embed(inputs=[chunk])
            sparse = next(self.sparse_model.embed([chunk]))  # type: ignore  # ruff:ignore[blanket-type-ignore]
            indices = sparse.indices.tolist()
            values = sparse.values.tolist()
            points.append(
                models.PointStruct(
                    id=str(uuid4()),
                    vector={
                        "dense": dense_vector[0],
                        "bm25": models.SparseVector(
                            indices=indices,
                            values=values,
                        ),
                    },
                    payload=metadata or {},
                )
            )

        await self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )
        logger.info(
            "Finished indexing text, time %s seconds", round(time.monotonic() - start_time, 2)
        )

    async def retrieve_documents(
        self,
        query: str,
        limit: int = 5,
        prefetch_limit: int = 25,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[str]:
        """Hybrid search: Dense + BM25 + RRF + Rerank."""
        dense_query = (await embed(inputs=[query]))[0]
        sparse_query = next(self.sparse_model.embed([query]))  # type: ignore  # ruff:ignore[blanket-type-ignore]

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

            qdrant_filter = models.Filter(must=conditions)  # type: ignore  # ruff:ignore[blanket-type-ignore]

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
            candidates.append({
                "id": p.id,
                "text": text,
                "payload": payload,
            })
            texts.append(text)

        if not texts:
            return []

        # rerank возвращает list[dict] с index, relevance_score, document
        # уже отсортирован по relevance_score desc, берём топ limit
        rerank_results = await rerank(query=query, documents=texts, top_n=limit)

        return [
            (
                f"**Relevance score:** {round(r['relevance_score'], 2)}\n"
                f"**Source:** {candidates[r['index']]['payload'].get('source', '')}\n"
                f"**Category:** {candidates[r['index']]['payload'].get('category', '')}\n"
                "**Document:**\n"
                f"{r['document']}"
            )
            for r in rerank_results
        ]
