import io

import pandas as pd

from src.utils import current_datetime


def create_students_list_file_template(
        course_title: str, group_title: str, add_instruction_sheet: bool = True
) -> bytes:
    """Создаёт шаблон Excel файла для заполнения списка студентов.

    :param course_title: Название курса.
    :param group_title: Название группы.
    :param add_instruction_sheet: Добавить лист с инструкцией
    """

    df_template = pd.DataFrame(columns=["ФИО"])
    buffer = io.BytesIO()
    with pd.ExcelWriter(
        buffer, engine="openpyxl", datetime_format="dd.mm.yyyy"
    ) as writer:
        df_template.to_excel(writer, sheet_name="Список студентов", index=False)
        if add_instruction_sheet:
            instructions = pd.DataFrame({
                "Инструкция": [
                    "1. Заполните колонку «ФИО» для каждого студента",
                    "2. Одна строка — один студент",
                    "3. ФИО пишите полностью (Фамилия Имя Отчество)",
                    "4. Не удаляйте и не переименовывайте заголовок «ФИО»",
                    "5. Пустые строки в конце файла можно удалить",
                    f"Курс: {course_title}",
                    f"Группа: {group_title}",
                    f"Создан: {current_datetime().strftime('%d.%m.%Y %H:%M')}"
                ]
            })
            instructions.to_excel(writer, sheet_name="Инструкция", index=False)
    buffer.seek(0)
    return buffer.getvalue()
