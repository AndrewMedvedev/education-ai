from pydantic_settings import SettingsConfigDict

from src.shared.infra.services import SrvBaseConfig


class SrvOrganizationConfig(SrvBaseConfig):
    model_config = SettingsConfigDict(env_prefix="SRV_ORGANIZATION_")
