from aiogram.fsm.state import State, StatesGroup


class StudentSignUpForm(StatesGroup):
    in_group_selecting = State()
    full_name_typing = State()


class TeacherSignUpForm(StatesGroup):
    password = State()
