from pydantic_settings import SettingsConfigDict

from src.shared.infra.services import SrvBaseConfig


class SrvLLMRouterConfig(SrvBaseConfig):
    model_config = SettingsConfigDict(env_prefix="SRV_LLM_ROUTER_")
