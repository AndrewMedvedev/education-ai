from taskiq import PrometheusMiddleware, SmartRetryMiddleware
from taskiq_aio_pika import AioPikaBroker, Exchange, Queue
from taskiq_fastapi import init

from .rabbit import rabbit_config

taskiq_broker = AioPikaBroker(
    rabbit_config.uri,
    qos=25,
    exchange=Exchange(
        name="myapp_exchange",
        durable=True,
    ),
    task_queues=[
        Queue(
            name="myapp_tasks",
            routing_key="myapp_tasks",
            durable=True,
        ),
    ],
    delay_queue=Queue(
        name="myapp_tasks.delay",
        durable=True,
    ),
    dead_letter_queue=Queue(
        name="myapp_tasks.dead_letter",
        durable=True,
    ),
).with_middlewares(
    SmartRetryMiddleware(
        default_retry_count=6,
        default_delay=10,
        use_jitter=True,
        use_delay_exponent=True,
        max_delay_exponent=100,
    ),
    PrometheusMiddleware(server_port=9000),
)

init(taskiq_broker, "main:app")
