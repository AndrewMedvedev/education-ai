from openai import AsyncOpenAI

from .config import aitunnel_config, deepseek_config, proxy_api_config, yandex_cloud_config

ai_tunnel_client = AsyncOpenAI(
    api_key=aitunnel_config.key,
    base_url=aitunnel_config.base_url,
    max_retries=0,
    timeout=340,
)

proxy_api_client = AsyncOpenAI(
    api_key=proxy_api_config.key,
    base_url=proxy_api_config.base_url,
    max_retries=0,
    timeout=340,
)

deepseek_client = AsyncOpenAI(
    api_key=deepseek_config.api_key,
    base_url=deepseek_config.base_url,
    max_retries=0,
    timeout=340,
)

__all__ = [
    "ai_tunnel_client",
    "aitunnel_config",
    "deepseek_client",
    "proxy_api_client",
    "proxy_api_config",
    "yandex_cloud_config",
]
