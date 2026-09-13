import dramatiq
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from dramatiq.middleware.prometheus import Prometheus
from dramatiq.results import Results
from dramatiq.results.backends import RedisBackend

from .rabbit import rabbit_config
from .redis import redis_config

dramatiq_result_backend = RedisBackend(url=redis_config.url)
dramatiq_rabbitmq_broker = RabbitmqBroker(url=rabbit_config.uri)
dramatiq_rabbitmq_broker.add_middleware(Results(backend=dramatiq_result_backend))
dramatiq_rabbitmq_broker.add_middleware(dramatiq.middleware.AsyncIO())
dramatiq_rabbitmq_broker.add_middleware(Prometheus())
dramatiq.set_broker(dramatiq_rabbitmq_broker)
