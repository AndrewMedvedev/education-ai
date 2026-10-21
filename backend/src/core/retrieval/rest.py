from typing import Any

import operator

from aiohttp import ClientSession

from src.core.providers import ai_tunnel_client, aitunnel_config

from .config import embeddings_config, rerankers_config


async def embed(
    inputs: list[str],
) -> list[list[float]]:
    """Создаёт векторное представление текста."""

    response = await ai_tunnel_client.embeddings.create(
        model=embeddings_config.model_name,
        input=inputs,
    )

    return [item.embedding for item in sorted(response.data, key=operator.attrgetter("index"))]


async def rerank(
    query: str,
    documents: list[str],
    top_n: int | None = None,
) -> list[dict[str, Any]]:
    async with ClientSession() as session:
        response = await session.post(
            "https://api.aitunnel.ru/v1/rerank",
            headers={
                "Authorization": f"Bearer {aitunnel_config.key}",
                "Content-Type": "application/json",
            },
            json={
                "model": rerankers_config.model_name,
                "query": query,
                "documents": documents,
                "top_n": top_n or len(documents),
            },
        )
        response.raise_for_status()
        result = await response.json()
        return sorted(
            result["results"],
            key=operator.itemgetter("relevance_score"),
            reverse=True,
        )
