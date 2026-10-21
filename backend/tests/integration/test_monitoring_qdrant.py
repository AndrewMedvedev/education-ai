"""Проверка метрик на пустой временной коллекции, без эмбеддингов и LLM."""

import os
from contextlib import closing
from uuid import uuid4

import pytest
from qdrant_client import QdrantClient, models


@pytest.mark.skipif(
    not os.getenv("TEST_QDRANT_URL"),
    reason="Explicit test Qdrant connection is required",
)
def test_rest_and_grpc_metrics():
    url = os.environ["TEST_QDRANT_URL"]
    api_key = os.environ.get("TEST_QDRANT_API_KEY")
    collection = f"monitoring-smoke-{uuid4()}"
    with closing(QdrantClient(url=url, api_key=api_key)) as rest:
        rest.create_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(size=4, distance=models.Distance.COSINE),
        )
        try:
            assert rest.count(collection, exact=True).count == 0
            with closing(QdrantClient(url=url, api_key=api_key, prefer_grpc=True)) as grpc:
                assert grpc.count(collection, exact=True).count == 0
        finally:
            rest.delete_collection(collection)
