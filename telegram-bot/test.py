import asyncio
import json
import logging
from uuid import UUID

import aiofiles

from src.ai_agents.course_structure_planner import CourseStructurePlan
from src.ai_agents.module_designer import DesignerContext, agent
from src.core import enums, schemas
from src.services import courses as courses_service
from src.services import media as media_service

logger = logging.getLogger(__name__)


async def main() -> None:
    user_id = 1779915071
    """attachments: list[schemas.Attachment] = []
    files = ["Лекция 1.pdf", "Лекция 2.pdf", "Лекция 3.pptx"]
    for file in files:
        async with aiofiles.open(file, mode="rb") as f:
            data = await f.read()
            attachment = await media_service.upload(user_id=user_id, filename=file, data=data)
            attachments.append(attachment)
    """
    attachments = [
        UUID("b2040a7b-8155-4b8a-83e8-1a4434f83337"),
        UUID("f7bb7f8d-76df-4112-87bf-2364cd7924a7"),
        UUID("f635c343-efe3-43df-b43c-07fcb1bb9a21"),
    ]
    teacher_inputs = schemas.TeacherInputs(
        user_id=user_id,
        discipline="Системы Искусственного интеллекта",
        target_audience="Студенты 3 курса IT-направлений Тюменского Индустриального Университета",
        difficulty_level=enums.DifficultyLevel.BEGINNER,
        comment="Курс идёт 1 семестр, в качестве языка программирования используй Python",
        attachments=attachments,
    )
    """task = await courses_service.confirm_creation(teacher_inputs)
    result = await agent.ainvoke(
        {"messages": []}, context=PlannerContext(
            user_id=user_id, course_id=task.resource_id, teacher_inputs=teacher_inputs
        )
    )
    print(result["structured_response"])
    with open("new_plan.json", "w", encoding="utf-8") as f:
        json.dump(result["structured_response"].model_dump_json(), f, indent=4, ensure_ascii=False)
    """
    with open("new_plan.json", "r", encoding="utf-8") as f:
        course_structure_plan = CourseStructurePlan.model_validate_json(json.load(f))
    course_id = UUID("6b073754254d44e593769af970356cb5")
    result = await agent.ainvoke(
        {"messages": []}, context=DesignerContext(
            course_id=course_id,
            teacher_inputs=teacher_inputs,
            course_description=course_structure_plan.description,
            module_note=course_structure_plan.module_notes[0]
        )
    )
    print(result["structured_response"])
    """
    with open("module_design_example.json", "w", encoding="utf-8") as f:
        json.dump(result["structured_response"].model_dump_json(), f, indent=4, ensure_ascii=False)
    """


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
