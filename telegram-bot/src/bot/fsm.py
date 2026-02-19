from aiogram.fsm.state import State, StatesGroup


class StudentSignUpForm(StatesGroup):
    """Форма регистрации для студента"""

    in_group_choice = State()
    waiting_for_full_name = State()


class TeacherSignUpForm(StatesGroup):
    """Форма регистрации преподавателя"""

    waiting_for_password = State()


class TestPassingForm(StatesGroup):
    """Форма для прохождения тестирования"""

    waiting_for_answer = State()
