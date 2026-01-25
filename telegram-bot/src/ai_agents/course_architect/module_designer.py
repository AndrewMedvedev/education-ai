import logging

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt
from langchain.agents.structured_output import ToolStrategy
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ...core.enums import ContentType
from ...settings import PROMPTS_DIR, settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
        PROMPTS_DIR / "course_architect" / "scenario_writer.md"
).read_text(encoding="utf-8")

model = ChatOpenAI(
    api_key=settings.yandexcloud.apikey,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.5,
    max_retries=3
)
