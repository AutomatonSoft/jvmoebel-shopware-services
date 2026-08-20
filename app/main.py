from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from core.config import settings
from core.errors_handlers import register_errors_handlers
from core.logger import configure_logging
from core.middleware import MaxBodySizeMiddleware
from domains.ar.router import router as ar_models_router


configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    MaxBodySizeMiddleware,
    max_size=settings.ar_max_body_size
)

register_errors_handlers(app)

app.include_router(ar_models_router, prefix="/api/v1")


@app.get("/hello/")
def hello(name: str = "World"):
    name = name.strip().title()
    return {"message": f"Hello {name}!"}


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
