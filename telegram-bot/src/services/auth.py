import logging
import secrets
import string
from uuid import UUID

from passlib.context import CryptContext
from pydantic import BaseModel, SecretStr

from ..core.exceptions import ForbiddenError
from ..core.schemas import Student
from ..database.base import session_factory
from ..database.repository import student as student_repo

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


class Credentials(BaseModel):
    login: str
    password: SecretStr


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
        password_hash = pwd_context.hash(password)
        student = Student(
            course_id=course_id,
            created_by=teacher_id,
            full_name=full_name,
            login=login,
            password_hash=password_hash,
        )
        await student_repo.save(session, student)
        await session.commit()
    return Credentials(login=login, password=SecretStr(password))


async def authenticate_student(user_id: int, login: str, password: str) -> Student:
    """Аутентифицирует студента на курс.

    :param user_id: Идентификатор пользователя.
    :param login: Логин, который был выдан преподавателем.
    :param password: Пароль, который был выдан преподавателем.
    :returns: Аутентифицированный студент со статусом `is_active` = True
    """

    logger.info("Starting authenticate student `%s`", user_id)
    async with session_factory() as session:
        student = await student_repo.get_by_login(session, login)
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
            student = await student_repo.activate(session, user_id)
            await session.commit()
            logger.info("Student `%s` activated", user_id)
    logger.info("Student `%s` authenticated successfully", user_id)
    return student
