import logging

import uvicorn
from fastapi import FastAPI

from src.api.routers import router

app = FastAPI(
    title="Education AI API",
    description="""\
    ...
    """,
    version="0.1.0",
)

app.include_router(router)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
