import logging
import sys

from pythonjsonlogger.json import JsonFormatter


def configure_logging(log_level: str = "INFO"):
    """Настройка логирования в формате JSON"""

    log_level = getattr(logging, log_level.upper(), logging.INFO)  # pyright: ignore[reportAssignmentType]

    formatter = JsonFormatter(
        fmt=(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(lineno)d %(pathname)s"
        ),
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "logger",
            "request_id": "request_id",
        },
        timestamp=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for old_handler in root_logger.handlers[:]:
        root_logger.removeHandler(old_handler)

    root_logger.addHandler(handler)

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)

    return root_logger
