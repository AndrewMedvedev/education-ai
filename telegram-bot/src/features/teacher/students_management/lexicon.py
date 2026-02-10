from aiogram.utils.formatting import Text, Underline, as_line, as_numbered_section

GROUP_CREATION_TEXT = Text(
    "Давайте добавим группу.",
    as_line(),
    as_line(),
    as_numbered_section(
        Underline("Для этого вам нужно:"),
        *[
            "Ввести название группы",
            "Заполнить список студентов по шаблону",
            ""
        ]
    ),
)
