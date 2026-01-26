import logging

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

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


class ScenarioContext(BaseModel):
    """Контекст агента для написания сценария курса"""

    teacher_insights: str  # Инсайты преподавателя полученные из интервью с ним


class CourseScenario(BaseModel):
    """JSON output для сценарий курса"""

    title: str = Field(description="Название курса")
    description: str = Field(description="Описание курса")
    audience_description: str = Field(description="Описание целевой аудитории курса")
    learning_objectives: list[str] = Field(description="Цели обучения")
    modules: list[str] = Field(
        description="""
        Описание каждого модуля по порядку, здесь должно быть:
         - ключевые темы / подтемы (то, без чего курс невозможен)
         - цели обучения модуля
         - план по достижению образовательных целей
         """
    )
    assessment_description: str = Field(description="Описание финального ассессмента")


@dynamic_prompt
def context_based_prompt(request: ModelRequest) -> str:
    return SYSTEM_PROMPT.format(insights=request.runtime.context.teacher_insights)


scenario_writer = create_agent(
    model=model,
    context_schema=ScenarioContext,
    middleware=[context_based_prompt],
    response_format=ToolStrategy(CourseScenario),
)
