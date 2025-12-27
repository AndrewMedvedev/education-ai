from aiogram.fsm.state import State, StatesGroup


class CourseCreationForm(StatesGroup):
    """Форма для создания курса

    Attributes:
        education_materials_media: Файлы с учебным материалом.
        additional_comments: Дополнительные замечания преподавателя.
    """

    education_materials_media = State()
    additional_comments = State()
