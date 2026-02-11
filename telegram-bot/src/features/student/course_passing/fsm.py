from aiogram.fsm.state import State, StatesGroup


class AIChatState(StatesGroup):
    asking_question = State()
