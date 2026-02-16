from enum import StrEnum
from uuid import UUID

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tg_bot.features.course.schemas import Module


class ModuleCbData(CallbackData, prefix="std_mdl"):
    group_id: UUID
    order: int


def get_accessible_modules_kb(group_id: UUID, modules: list[Module]) -> InlineKeyboardMarkup:
    """Клавиатура для получения списка доступных модулей"""

    builder = InlineKeyboardBuilder()
    modules = modules.copy()
    current_module = modules.pop(-1)
    for module in modules:
        builder.button(
            text=f"✅ {module.title}", callback_data=ModuleCbData(
                group_id=group_id, order=module.order
            ).pack()
        )
    builder.button(
        text=f"💻 {current_module.title}", callback_data=ModuleCbData(
            group_id=group_id, order=current_module.order
        ).pack()
    )
    builder.adjust(1)
    return builder.as_markup()


class ModuleMenuAction(StrEnum):
    THEORY = "theory"
    PRACTICE = "practice"
    ASK_AI = "ask_ai"
    BACK = "back"


class ModuleMenuCbData(CallbackData, prefix="std_mdl_menu"):
    student_id: UUID
    action: ModuleMenuAction


def get_module_menu_kb(student_id: UUID) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📖 Теория", callback_data=ModuleMenuCbData(
            student_id=student_id, action=ModuleMenuAction.THEORY
        ).pack()
    )
    builder.button(
        text="🎯 Практика", callback_data=ModuleMenuCbData(
            student_id=student_id, action=ModuleMenuAction.PRACTICE
        ).pack()
    )
    builder.button(
        text="🤖 Чат с AI", callback_data=ModuleMenuCbData(
            student_id=student_id, action=ModuleMenuAction.ASK_AI
        ).pack()
    )
    builder.button(
        text="🔙 Назад", callback_data=ModuleMenuCbData(
            student_id=student_id, action=ModuleMenuAction.BACK
        ).pack()
    )
    builder.adjust(1)
    return builder.as_markup()
