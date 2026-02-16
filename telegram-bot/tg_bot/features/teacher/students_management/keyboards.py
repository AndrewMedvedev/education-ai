from typing import Literal

from enum import StrEnum
from uuid import UUID

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class GroupsMenuAction(StrEnum):
    LIST_GROUPS = "list_groups"  # Список групп
    ADD_GROUP = "add_group"  # Добавить группу
    BACK = "back"


class GroupsMenuCbData(CallbackData, prefix="tchr_grp_menu"):
    course_id: UUID
    action: GroupsMenuAction


def get_groups_menu_kb(course_id: UUID) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📋 Мои группы", callback_data=GroupsMenuCbData(
            course_id=course_id, action=GroupsMenuAction.LIST_GROUPS
        ).pack()
    )
    builder.button(
        text="➕ Добавить группу", callback_data=GroupsMenuCbData(
            course_id=course_id, action=GroupsMenuAction.ADD_GROUP
        ).pack()
    )
    builder.button(
        text="🔙 Назад", callback_data=GroupsMenuCbData(
            course_id=course_id, action=GroupsMenuAction.BACK
        ).pack()
    )
    builder.adjust(1)
    return builder.as_markup()


class ConfirmCbData(CallbackData, prefix="tchr_cnfrm_grp_add"):
    course_id: UUID
    action: Literal["cancel", "continue"]


def get_confirm_kb(course_id: UUID) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="❌ Отмена", callback_data=ConfirmCbData(
            course_id=course_id, action="cancel"
        ).pack()
    )
    builder.button(
        text="🔜 Продолжить", callback_data=ConfirmCbData(
            course_id=course_id, action="continue"
        ).pack()
    )
    return builder.as_markup()
