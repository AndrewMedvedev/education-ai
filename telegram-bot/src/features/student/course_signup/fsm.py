from aiogram.fsm.state import State, StatesGroup


class SignupForm(StatesGroup):
    """Форма для ввода учетных данных"""

    in_login_typing = State()
    in_password_typing = State()
