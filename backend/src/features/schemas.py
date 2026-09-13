import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from qdrant_client import models

from src.core.database import session_factory
from src.core.qdrant import qdrant_client
from src.courses.agents.course_generator.helper import invoke_or_resume
from src.courses.agents.course_generator.nodes import Context, agent
from src.courses.agents.course_generator.serializer import checkpointer
from src.courses.agents.schemas import RuntimeContext

prompt = """курс домашний электрика и базовый электромонтаж 1 целевой аудитория и начальный уровень полный новичок без опыт профессиональный работа с электричество человек желать разобраться в принцип работа бытовой электросеть для безопасный выполнение базовый электромонтажный работа в квартира дом или для грамотный контроль сторонний специалист 2 образовательный цель результат обучение понимание принцип работа однофазный бытовой электросеть умение читать и составлять базовый принципиальный и монтажный схема электропроводка умение рассчитывать нагрузка и корректно подбирать сечение кабель и номинал защитный аппарат автоматический выключатель узо дифавтомат умение проектировать схема квартирный распределительный щит понимание правило безопасный монтаж и подключение розеточный группа выключатель и осветительный прибор твёрдый знание правило электробезопасность алгоритм снятие и проверка отсутствие напряжение а также чёткий понимание граница свой компетенция и ситуация требовать вызов квалифицировать электрика 3 структура и ключевой тема курс блок 1 физический и теоретический основа понятие напряжение сила ток сопротивление электрический мощность закон ома для участок цепь и расчёт мощность p u i постоянный и переменный ток 50 гц понятие фаза l рабочий ноль n и защитный заземление pe их назначение и отличие блок 2 компонент электросеть и расчёт чтение базовый электрический схема и условный обозначение кабельный продукция тип кабель ввг нг ls и др материал медь vs алюминий выбор сечение проводник по токовый нагрузка и допустимый потеря защитный аппаратура назначение принцип работа и различие автоматический выключатель характеристика b c узо ток утечка тип a ac и дифференциальный автомат расчёт суммарный и групповой нагрузка бытовой прибор устройство и компоновка квартирный распределительный щит блок 3 проектирование и базовый монтаж проектирование групповой линия домашний электропроводка освещение розетка силовой прибор способ соединение проводник клеммник опрессовка пайка сварка и запрет на простой скрутка схема и правило подключение розетка одноклавишный и двухклавишный выключатель проходная переключатель освещение блок 4 электробезопасность и регламент работа опасность электрический ток и физиология поражение золотой правило безопасность отключение питание блокировка от случайный включение обязательный проверка отсутствие напряжение указатель мультиметр принцип работа система заземление tn c tn c s tt и защитный отключение разграничение зона ответственность что допустимый делать свой рука а где обязательный допуск и квалифицировать специалист работа под напряжение вводный стояк опломбировать узел блок 5 продвинуть блок специфика частное дом трехфазный ввод трехфазный ввод 380 в 220 в распределение нагрузка по фаза и перекос фаза система заземление для частное дом и организация контур заземление узип устройство защита от импульсный перенапряжение и основа молниезащита 4 типичный ошибка разбор который обязательный завышение номинал автомат при он частый срабатывание жучок установка автомат 25а на кабель 1 5 мм² неправильный подбор сечение кабель под планировать нагрузка путаница между фаза рабочий нуль n и защитный нуль pe опасный объединение n и pe после точка разделение или в розетка зануление отсутствие узо во влажный зона или неверный выбор уставка тип узо работа без снятие напряжение или без предварительный проверка прибор прямой соединение медь и алюминий без переходный клемма использование ненадёжный скрутка в распределительный коробка перегрузка розеточный линия через тройник и удлинитель 5 методический акцент подача материал с объяснение причинный следственный связь почему возникнуть ошибка что происходить в цепь физически к что это привести как сделать правильно фокус на базовый однофазный сеть квартира с последующий расширение на трехфазный сеть частный дом акцент на безопасность правильный диагностик и недопустимость опасный работа под напряжение
"""  # ruff:ignore[line-too-long]


def configure_logging(level=logging.INFO):
    """Выполняет действие `configure_logging`, чтобы поддержать основной сценарий модуля."""
    logging.basicConfig(
        level=level,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s - %(message)s",
    )


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        """Выполняет действие `default`, чтобы поддержать основной сценарий модуля."""
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


async def main():
    configure_logging()

    course_id = UUID("693e6c1a-44a5-46f1-a7b3-d94345a670ee")
    user_id = UUID("3887cb68-d0ab-46d0-9f15-d13d4b4fc78f")

    await checkpointer.setup()  # pyright: ignore[reportAttributeAccessIssue]

    exists = await qdrant_client.collection_exists("MAIN_COLLECTION")

    if not exists:
        await qdrant_client.create_collection(
            collection_name="MAIN_COLLECTION",
            vectors_config={
                "dense": models.VectorParams(
                    size=1024,
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={
                "bm25": models.SparseVectorParams(),
            },
        )

    # ВАЖНО: уже за пределами `if not exists`
    async with session_factory() as db_session:
        result = await invoke_or_resume(
            graph=agent,
            input_data={
                "generation_context": Context(
                    user_id=user_id,
                    course_id=course_id,
                    prompt=prompt,
                ),
            },
            context=RuntimeContext(
                db_session=db_session,
            ),
            config=RunnableConfig(
                configurable={
                    "thread_id": f"course:{course_id}",
                }
            ),
        )

    serializable_result = {}

    for key, value in result.items():
        if hasattr(value, "model_dump"):
            serializable_result[key] = value.model_dump()
        elif hasattr(value, "dict"):
            serializable_result[key] = value.dict()
        elif isinstance(value, UUID):
            serializable_result[key] = str(value)
        else:
            serializable_result[key] = value

    output_dir = Path("results")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "course_result.json"

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(
            serializable_result,
            f,
            ensure_ascii=False,
            indent=2,
            cls=UUIDEncoder,
        )

    print(f"Результат сохранён в {output_file.absolute()}")


if __name__ == "__main__":
    asyncio.run(main())
