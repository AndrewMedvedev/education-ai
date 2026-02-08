import logging

import uvicorn

from src.core.app import app
from src.features.teacher.views import router as teacher_views_router


def configure_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s - %(message)s",
    )


if __name__ == "__main__":
    configure_logging()

    app.include_router(teacher_views_router)

    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
