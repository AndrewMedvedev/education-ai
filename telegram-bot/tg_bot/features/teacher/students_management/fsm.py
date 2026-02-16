from aiogram.fsm.state import State, StatesGroup


class GroupCreationForm(StatesGroup):
    in_title_typing = State()
    waiting_for_students_list = State()
