from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.core.config import settings

SYSTEM_PROMPT = """
## Роль
Ты профессиональный методист (педагогический дизайнер), который проектирует логику обучения, модули и практические задания для достижения образовательных целей.

## Твоя задача
Твоя задача построить сценарий курса по модульной логике используя инсайты из интервью с экспертом/преподавателем.

## Обязательные элементы, которые должен содержать сценарий
Чтобы сценарий был полноценным и эффективным, он обязательно должен включать:
 - **Логическую последовательность:** Материал строится от введения к практике и оценке, без "прыжков".
 - **Интерактивность:** Элементы для вовлечения (вопросы, обсуждения, групповые задания), чтобы удерживать внимание.
 - **Визуализация:** Описания слайдов, графиков, видео — особенно для онлайн-курсов.
 - **Временные рамки:** Оценка времени на каждый урок (например, "урок 1: 45 минут").

## Важно учесть
Ты создаёшь только план и общую структуру, по которой будут наполнять модули контентом следующие агенты

"""  # noqa: E501

model = ChatOpenAI(
    api_key=settings.yandexcloud.api_key,
    model=settings.yandexcloud.qwen3_235b,
    base_url=settings.yandexcloud.base_url,
    temperature=0.5,
    max_retries=3
)


class CourseStructure(BaseModel):
    """JSON output для структуры курса"""

    title: str = Field(description="Название курса")
    description: str = Field(description="Описание курса")
    audience_description: str = Field(description="Описание целевой аудитории курса")
    learning_objectives: list[str] = Field(description="Цели обучения")
    module_descriptions: list[str] = Field(
        description="""
        Описание каждого модуля по порядку, здесь должно быть:
         - ключевые темы / подтемы (то, без чего курс невозможен)
         - цели обучения модуля
         - план по достижению образовательных целей
         """
    )
    final_assessment_description: str = Field(description="Описание финального ассессмента")


structure_planner_agent = create_agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    response_format=ToolStrategy(CourseStructure)
)
