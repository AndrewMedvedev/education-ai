from aiogram.filters.callback_data import CallbackData


class StartCBData(CallbackData, prefix="start"):
    tg_user_id: int
