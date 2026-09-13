import os
from concurrent.futures import ThreadPoolExecutor

from tiktoken import get_encoding

MAX_WORKERS = max(1, (os.cpu_count() or 2) // 2)

tokens_encoder = get_encoding("o200k_base")

# В `lifespan` вызвать `thread_executor.shutdown(wait=True)`
thread_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="thread_worker")
