from typing import Any

import logging

import aiohttp

logger = logging.getLogger(__name__)


async def search_videos(query: str, videos_count: int = 10) -> list[dict[str, Any]]:
    async with (
        aiohttp.ClientSession(base_url="https://rutube.ru/api/") as session,
        session.get(url="search/video", params={"query": query}) as response,
    ):
        data = await response.json()
    return [
        {
            "title": result["title"],
            "description": result["description"],
            "author_name": result["author"]["name"],
            "video_url": result["video_url"],
            "duration": result["duration"],
            "published_at": result["publication_ts"],
        }
        for result in data["results"][:videos_count]
    ]
