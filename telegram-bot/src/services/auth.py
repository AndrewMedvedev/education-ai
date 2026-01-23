from typing import TypedDict

import secrets
import string
from uuid import UUID

from ..core.schemas import Student
from ..database.base import session_factory
from ..database.repository import student as student_repo


class Credentials(TypedDict):
    login: str
    password: str


def _make_student_login(full_name: str, serial_number: int) -> str:
    """Создаёт логин для студента по его ФИО и порядковы номер.

    :param ФИО студента.
    :param serial_number: Порядковый номер при записи на курс.
    """

    surname = full_name.split(maxsplit=1)[0].lower()
    initials = "".join([name[0].lower() for name in full_name.split()[1:]])
    return f"{surname}_{initials}_{serial_number}"


def generate_password(chars_count: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(chars_count))


async def generate_student_credentials(
        course_id: UUID, teacher_id: int, full_name: str
) -> Credentials:
    """Генерирует пару логин + пароль для студента, чтобы получить доступ к курсу.

    :param course_id: Идентификатор курса.
    :param teacher_id: Идентификатор преподавателя.
    :param full_name: ФИО студента.
    """

    async with session_factory() as session:
        students_count = await student_repo.get_count(session, course_id)
        login = _make_student_login(full_name, students_count)
        password = generate_password()
        student = Student(
            course_id=course_id,
            created_by=teacher_id,
            full_name=full_name,
            login=login,
            password_hash=...
        )
        await student_repo.save(session, student)
        await session.commit()
    return {"login": login, "password": password}
