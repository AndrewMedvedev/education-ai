from typing import Any

import logging

import aiohttp

logger = logging.getLogger(__name__)

BASE_URL = "https://rutube.ru/api/"


async def search_video(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    headers = {"Content-Type": "application/json"}
    async with aiohttp.ClientSession(base_url=BASE_URL) as session, session.get(
            url="search/video", params={"query": query}, headers=headers
    ) as response:
        data = await response.json()
    return [
        {
            "id": result["id"],
            "title": result["title"],
            "description": result["description"],
            "author_name": result["author"]["name"],
            "video_url": result["video_url"],
            "duration": result["duration"],
            "published_at": result["publication_ts"],
        }
        for result in data["results"][:max_results]
    ]


async def get_video(video_id: str) -> dict[str, Any]:
    async with aiohttp.ClientSession(base_url=BASE_URL) as session, session.get(
        url=f"video/{video_id}", headers={"Content-Type": "application/json"}
    ) as response:
        data = await response.json()
    return {
        "id": data["id"],
        "title": data["title"],
        "description": data["description"],
        "video_url": data["video_url"],
        "duration": data["duration"],
        "is_adult": data["is_adult"],
        "hashtags": data["hashtags"],
    }
