import logging
import secrets
import string
from uuid import UUID

from passlib.context import CryptContext
from pydantic import SecretStr

from tg_bot.core.database import session_factory
from tg_bot.features.student import repository
from tg_bot.features.student.schemas import Student

from .schemas import Credentials

# Хеширование паролей
MEMORY_COST = 100  # Размер выделяемой памяти в mb
TIME_COST = 2
PARALLELISM = 2
SALT_SIZE = 16
ROUNDS = 14  # Количество раундов для хеширования

logger = logging.getLogger(__name__)

pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    default="argon2",
    argon2__memory_cost=MEMORY_COST,
    argon2__time_cost=TIME_COST,
    argon2__parallelism=PARALLELISM,
    argon2__salt_size=SALT_SIZE,
    bcrypt__rounds=ROUNDS,
    deprecated="auto"
)


class ForbiddenError(Exception):
    pass


def _build_student_login(full_name: str, serial_number: int) -> str:
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


async def create_student_credentials(group_id: UUID, full_names: list[str]) -> list[Credentials]:
    credentials = []
    async with session_factory() as session:
        students = await repository.get_students_by_group(session, group_id)
        students_count = len(students)
        for full_name in full_names:
            login = _build_student_login(full_name, students_count)
            password = generate_password()
            password_hash = pwd_context.hash(password)
            student = Student(
                group_id=group_id,
                full_name=full_name,
                login=login,
                password_hash=password_hash,
            )
            await repository.add_student(session, student)
            await session.flush()
            cred = Credentials(full_name=full_name, login=login, password=SecretStr(password))
            credentials.append(cred)
            students_count += 1
        await session.commit()
    return credentials


async def authenticate_student(user_id: int, login: str, password: str) -> Student:
    """Аутентифицирует студента на курс.

    :param user_id: Идентификатор пользователя.
    :param login: Логин, который был выдан преподавателем.
    :param password: Пароль, который был выдан преподавателем.
    :returns: Аутентифицированный студент со статусом `is_active` = True
    """

    logger.info("Starting authenticate student `%s`", user_id)
    async with session_factory() as session:
        student = await repository.get_student_by_login(session, login)
        if student is None:
            logger.warning(
                "Student `%s` is not registered, login `%s` does not exist!",
                user_id, login
            )
            raise ForbiddenError(
                f"Student `{user_id}` is not registered, login `{login}` does not exist!"
            )
        if not pwd_context.verify(password, student.password_hash):
            logger.warning("Student `%s` entered wrong password!", user_id)
            raise ForbiddenError(f"Student `{user_id}` entered wrong password!")
        if not student.is_active:
            logger.info("Student `%s` is not active, starting activation")
            student = await repository.activate_student(session, student.id, user_id=user_id)
            await session.commit()
            logger.info("Student `%s` activated", user_id)
    logger.info("Student `%s` authenticated successfully", user_id)
    return student
