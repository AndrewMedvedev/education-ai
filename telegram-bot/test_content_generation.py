import json
import logging

from src.ai_agents.content_block_generator import PlannerContext, agent, planner
from src.ai_agents.module_designer import ModuleDesign


def main() -> None:

    with open("module_design_example.json", encoding="utf-8") as f:
        module_design = ModuleDesign.model_validate_json(json.load(f))

    content_block = module_design.content_blueprint[1]
    context = PlannerContext(
        module_title="Введение в искусственный интеллект",
        module_description="""Введение в ИИ: история, основные направления, области применения.
        Базовые термины и понятия. Роль Python в разработке ИИ‑систем.""",
        learning_sequence=module_design.learning_sequence,
        content_block=content_block
    )
    result = agent.invoke({"input": context})
    print(result)  # noqa: T201
    print("################################################################")
    print("################################################################")
    print("################################################################")
    print(result["response"])

    """with open(
            f"content_block_{content_block.block_type}_example.json", "w", encoding="utf-8"
    ) as f:
        json.dump(result["structured_response"], f, indent=4)"""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
