from pydantic_settings import SettingsConfigDict

from src.shared.infra.services import SrvBaseConfig


class SrvCourseConfig(SrvBaseConfig):
    model_config = SettingsConfigDict(env_prefix="SRV_COURSE_")
