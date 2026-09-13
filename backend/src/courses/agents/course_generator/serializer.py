from typing import cast

from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.checkpoint.redis.jsonplus_redis import JsonPlusRedisSerializer

from src.core.redis import checkpointer as base_checkpointer

serializer = JsonPlusRedisSerializer(
    allowed_json_modules=[
        (
            "src",
            "courses",
            "agents",
            "schemas",
            "Context",
        ),
        (
            "src",
            "courses",
            "agents",
            "course_generator",
            "subagents",
            "prompts",
            "CourseStructure",
        ),
        (
            "src",
            "courses",
            "agents",
            "course_generator",
            "subagents",
            "prompts",
            "ModuleStructure",
        ),
        (
            "src",
            "courses",
            "agents",
            "course_generator",
            "subagents",
            "prompts",
            "LessonStructure",
        ),
        (
            "src",
            "courses",
            "agents",
            "course_generator",
            "subagents",
            "prompts",
            "ContentSpecification",
        ),
    ],
    allowed_msgpack_modules=[
        (
            "src.courses.agents.schemas",
            "Context",
        ),
        (
            "src.courses.agents.course_generator.subagents.prompts",
            "CourseStructure",
        ),
        (
            "src.courses.agents.course_generator.subagents.prompts",
            "ModuleStructure",
        ),
        (
            "src.courses.agents.course_generator.subagents.prompts",
            "LessonStructure",
        ),
        (
            "builtins",
            "ExceptionGroup",
        ),
        (
            "builtins",
            "BaseExceptionGroup",
        ),
    ],
)


checkpointer = cast(
    AsyncRedisSaver,
    base_checkpointer,
)

checkpointer.serde = serializer
