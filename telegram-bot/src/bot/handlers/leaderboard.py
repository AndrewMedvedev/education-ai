from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.infra.db.conn import session_factory
from src.infra.db.repos import StudentRepository

from ..lexicon import CONFETTI_EFFECT_ID

router = Router(name=__name__)

rank_to_emoji_map = {
    1: "🥇",
    2: "🥈",
    3: "🥉",
    4: "4️⃣",
    5: "5️⃣",
}


@router.message(Command("leaderboard"))
async def cmd_leaderboard(message: Message) -> None:
    """Просмотр доски лидеров курса"""

    async with session_factory() as session:
        student_repo = StudentRepository(session)
        group = await student_repo.get_student_group(message.from_user.id)
        leaders = await student_repo.get_leaders(group.course_id, group.id)
    current_leader = next(
        (leader for leader in leaders if leader.user_id == message.from_user.id), None
    )
    if current_leader is not None:
        await message.answer(
            text=f"Поздравляем 🎉! Вы в списке лидеров на <b>{current_leader.rank}</b> месте!",
            message_effect_id=CONFETTI_EFFECT_ID,
        )
    await message.answer(
        text=(
            "<b>🏆 Доска лидеров</b>\n\n"
            f"{
                '\n'.join(
                    f'{rank_to_emoji_map[leader.rank]} '
                    f'<i>{leader.full_name}</i> - '
                    f'<b>{leader.total_score}</b>'
                    for leader in leaders
                )
            }"
        ),
    )
