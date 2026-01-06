import logging

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from langchain_openai import ChatOpenAI

from ..core import schemas
from ..settings import PROMPTS_DIR, settings
from .course_structure_planner import ModuleNote

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (PROMPTS_DIR / "module_generator.md").read_text(encoding="utf-8")

llm = ChatOpenAI(
    api_key=settings.yandexcloud.apikey,
    model=settings.yandexcloud.aliceai_llm,
    base_url=settings.yandexcloud.base_url,
    temperature=0,
    max_retries=3
)


async def generate_module(discipline: str, module_note: ModuleNote) -> schemas.Module:
    logger.info("Generating %s module of discipline %s", module_note.order, discipline)
    parser = PydanticOutputParser(pydantic_object=schemas.Module)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
    ]).partial(format_instructions=parser.get_format_instructions())
    chain: RunnableSerializable[dict[str, str], schemas.Module] = prompt | llm | parser
    return await chain.ainvoke({
        "discipline": discipline, "module_note": module_note.model_dump_json(),
    })
