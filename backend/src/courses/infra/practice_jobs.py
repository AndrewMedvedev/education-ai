"""Short-lived, user-scoped status for practice generation tasks."""
import json
from uuid import UUID, uuid4

from src.core.redis import redis_client

QUEUED_TTL = 180
RUNNING_TTL = 3900
FINISHED_TTL = 86400

_REPLACE = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    redis.call('SET', KEYS[1], ARGV[2], 'EX', ARGV[3])
    return 1
end
return 0
"""


def key(user_id: UUID, module_id: UUID, lesson_id: UUID) -> str:
    return f"practice-generation:{user_id}:{module_id}:{lesson_id}"


async def read(user_id: UUID, module_id: UUID, lesson_id: UUID) -> dict | None:
    value = await redis_client.get(key(user_id, module_id, lesson_id))
    return json.loads(value) if value else None


async def begin(user_id: UUID, module_id: UUID, lesson_id: UUID) -> tuple[dict, bool]:
    redis_key = key(user_id, module_id, lesson_id)
    while True:
        raw = await redis_client.get(redis_key)
        old = json.loads(raw) if raw else None
        if old and old["status"] in ("queued", "running"):
            return old, False
        job = {"job_id": str(uuid4()), "status": "queued"}
        new = json.dumps(job)
        if raw:
            accepted = await redis_client.eval(_REPLACE, 1, redis_key, raw, new, QUEUED_TTL)
        else:
            accepted = await redis_client.set(redis_key, new, ex=QUEUED_TTL, nx=True)
        if accepted:
            return job, True


async def transition(
    user_id: UUID,
    module_id: UUID,
    lesson_id: UUID,
    job_id: str,
    allowed: tuple[str, ...],
    status: str,
    ttl: int,
) -> bool:
    redis_key = key(user_id, module_id, lesson_id)
    while raw := await redis_client.get(redis_key):
        old = json.loads(raw)
        if old.get("job_id") != job_id or old.get("status") not in allowed:
            return False
        new = json.dumps({"job_id": job_id, "status": status})
        if await redis_client.eval(_REPLACE, 1, redis_key, raw, new, ttl):
            return True
    return False
