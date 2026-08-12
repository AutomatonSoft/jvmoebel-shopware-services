from contextlib import asynccontextmanager

from fastapi import FastAPI

import uvicorn

from core.logger import configure_logging



#import core.db.models # разобраться зачем этот импорт. без него пятисотил поинт просмотра пользователя по айди
from domains.ar.router import router as products_router

configure_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(products_router)

@app.get("/hello/")
def hello(name: str = "World"):
    name = name.strip().title()
    return {"message": f"Hello {name}!"}


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
