from enum import StrEnum
from uuid import UUID

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tg_bot.features.course.schemas import Course


class MenuAction(StrEnum):
    LIST_COURSES = "list_courses"  # Посмотреть список курсов
    SIGNUP_FOR_COURSE = "signup"  # Записаться на курс


class MenuCBData(CallbackData, prefix="std_menu"):
    action: MenuAction


def get_main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📚 Мои курсы",
        callback_data=MenuCBData(action=MenuAction.LIST_COURSES).pack(),
    )
    builder.button(
        text="🔑 Регистрация на курс",
        callback_data=MenuCBData(action=MenuAction.SIGNUP_FOR_COURSE).pack(),
    )
    builder.adjust(1)
    return builder.as_markup()


class CourseMenuAction(StrEnum):
    """Возможные действия в меню курса"""

    START_STUDYING = "strt_study"
    MY_PROGRESS = "my_progress"
    FEEDBACK = "feedback"
    BACK_TO_MAIN_MENU = "back"


class CourseMenuCbData(CallbackData, prefix="std_crs_menu"):
    student_id: UUID
    action: CourseMenuAction


def get_course_menu_kb(student_id: UUID) -> InlineKeyboardMarkup:
    """Клавиатура меню курса"""

    builder = InlineKeyboardBuilder()
    builder.button(
        text="🚀 Начать обучение", callback_data=CourseMenuCbData(
            student_id=student_id, action=CourseMenuAction.START_STUDYING
        ).pack()
    )
    builder.adjust(1)
    builder.button(
        text="📈 Успеваемость", callback_data=CourseMenuCbData(
            student_id=student_id, action=CourseMenuAction.MY_PROGRESS
        ).pack()
    )
    builder.button(
        text="📢 Обратная связь", callback_data=CourseMenuCbData(
            student_id=student_id, action=CourseMenuAction.FEEDBACK
        ).pack()
    )
    builder.adjust(2)
    builder.button(
        text="⚙️ В главное меню", callback_data=CourseMenuCbData(
            student_id=student_id, action=CourseMenuAction.BACK_TO_MAIN_MENU
        ).pack()
    )
    builder.adjust(1)
    return builder.as_markup()


class CourseCbData(CallbackData, prefix="std_crs"):
    course_id: UUID


def get_list_courses_kb(courses: list[Course]) -> InlineKeyboardMarkup:
    """Клавиатура для получения списка курсов студента"""

    builder = InlineKeyboardBuilder()
    for course in courses:
        builder.button(
            text=f"{course.title}", callback_data=CourseCbData(course_id=course.id).pack()
        )
    return builder.as_markup()
