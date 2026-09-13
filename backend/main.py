import uvicorn

from src import router
from src.core.fastapi import app
from src.core.settings import app_config
from src.shared.api.exception_handler import setup_exception_handlers

app.include_router(router)

setup_exception_handlers(app)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=app_config.port)
