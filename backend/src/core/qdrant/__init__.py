from qdrant_client import AsyncQdrantClient

from .config import qdrant_config

qdrant_client = AsyncQdrantClient(url=qdrant_config.url, api_key=qdrant_config.api_key)
