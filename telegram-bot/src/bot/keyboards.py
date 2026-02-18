from typing import Literal

from enum import StrEnum
from uuid import UUID

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.core.entities.course import Module
from src.core.entities.student import Group
from src.core.entities.user import UserRole


class UserChoiceCbData(CallbackData, prefix="role_choice"):
    role: UserRole


def get_role_choice_kb() -> InlineKeyboardMarkup:
    """Inline клавиатура для выбора роли"""

    builder = InlineKeyboardBuilder()
    builder.button(
        text="🧑🏻‍🎓 Студент", callback_data=UserChoiceCbData(role=UserRole.STUDENT).pack()
    )
    builder.button(
        text="🧑🏻‍🏫 Преподаватель", callback_data=UserChoiceCbData(role=UserRole.TEACHER).pack()
    )
    builder.adjust(1)
    return builder.as_markup()


class GroupChoiceCbData(CallbackData, prefix="group_choice"):
    group_id: UUID


def get_group_choice_kb(groups: list[Group]) -> InlineKeyboardMarkup:
    """Клавиатура для выбора группы"""

    builder = InlineKeyboardBuilder()
    for group in groups:
        builder.button(
            text=group.title, callback_data=GroupChoiceCbData(group_id=group.id).pack()
        )
    builder.adjust(1)
    return builder.as_markup()


class ConfirmSignUpCbData(CallbackData, prefix="confirm_signup"):
    action: Literal["ok", "cancel"] = "ok"


def get_confirm_sign_up_kb() -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения регистрации на курс"""

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Всё верно", callback_data=ConfirmSignUpCbData().pack())
    builder.button(text="❌ Отмена", callback_data=ConfirmSignUpCbData(action="cancel").pack())
    return builder.as_markup()


class ModuleCbData(CallbackData, prefix="module"):
    module_id: UUID


def get_modules_kb(modules: list[Module], current_module_id: UUID) -> InlineKeyboardMarkup:
    """Клавиатура со списком модулей курса"""

    current_order = next(
        (order for order, module in enumerate(modules) if module.id == current_module_id), None
    )
    builder = InlineKeyboardBuilder()
    for order, module in enumerate(modules):
        if current_order is not None and order <= current_order:
            btn_text = f"🔓 {module.title}"
        else:
            btn_text = f"🔒 {module.title}"
        builder.button(
            text=btn_text, callback_data=ModuleCbData(module_id=module.id).pack()
        )
    builder.adjust(1)
    return builder.as_markup()


class ModuleAction(StrEnum):
    STUDY_THEORY = "study_theory"
    TAKE_TEST = "take_test"


class ModuleStudyCbData(CallbackData, prefix="module_learn"):
    action: ModuleAction


def get_module_study_kb() -> InlineKeyboardMarkup:
    """Клавиатура для изучения модуля"""

    builder = InlineKeyboardBuilder()
    builder.button(
        text="💻 Приступить к изучению",
        callback_data=ModuleStudyCbData(action=ModuleAction.STUDY_THEORY).pack()
    )
    builder.button(
        text="🎯 Пройти тестирование",
        callback_data=ModuleStudyCbData(action=ModuleAction.TAKE_TEST).pack()
    )
    builder.adjust(1)
    return builder.as_markup()
