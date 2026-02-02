from typing import Any

from ddgs import DDGS


def search(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    return DDGS().text(query, region="ru-ru", max_results=max_results)


def search_books(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    return DDGS().books(query, region="ru-ru", max_results=max_results)


def search_video(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    return DDGS().videos(query, region="ru-ru", max_results=max_results)
