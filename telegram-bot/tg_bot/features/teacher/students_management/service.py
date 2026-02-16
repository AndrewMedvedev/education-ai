from uuid import UUID

from tg_bot.features.auth.service import create_student_credentials
from tg_bot.features.auth.utils import (
    extract_student_full_names,
    generate_student_credentials_file,
)


async def add_students_in_group(group_id: UUID, excel_file: bytes) -> bytes:
    """Добавление студентов в группу.

    :param group_id: ID группы в которую нужно добавить студентов.
    :param excel_file: Заполненный по шаблону список студентов (ФИО).
    :returns: Excel файл с учётными данными студентов.
    """

    full_names = extract_student_full_names(excel_file)
    credentials = await create_student_credentials(group_id, full_names)
    return generate_student_credentials_file(credentials)
