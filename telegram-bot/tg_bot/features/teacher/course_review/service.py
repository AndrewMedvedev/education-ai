from tg_bot.features.course.schemas import AnyContentBlock

from ..course_creation.ai_agent.agents.theory_generator import (
    ModuleContext,
    call_content_generator,
)


async def refactor_content_block(
        current_content_block: AnyContentBlock,
        teacher_query: str,
        module_title: str,
        module_description: str,
) -> AnyContentBlock:
    """Рефакторинг контента с помощью AI агента.

    :param current_content_block: Контент, который нужно отредактировать.
    :param teacher_query: Запрос преподавателя.
    :param module_title: Название модуля.
    :param module_description: Описание модуля.
    """

    prompt_template = f"""\
    Следуй инструкциям преподавателя для редактирования контента:

    ## Контент блок, который нужно отредактировать:
    {current_content_block.model_dump()}

    ## Запрос преподавателя:
    {teacher_query}
    """
    return await call_content_generator(
        content_type=current_content_block.content_type,
        prompt=prompt_template,
        context=ModuleContext(
            title=module_title, description=module_description,
        )
    )
