# app/main.py
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from core.config import settings
from core.errors_handlers import register_errors_handlers
from core.logger import configure_logging
from domains.ingestion.router import router as ingestion_router
from domains.journeys.router import router as journeys_router
from domains.reports.router import router as reports_router

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)

register_errors_handlers(app)
app.include_router(ingestion_router, prefix=settings.api_v1_prefix)
app.include_router(reports_router, prefix=settings.api_v1_prefix)
app.include_router(journeys_router, prefix=settings.api_v1_prefix)

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
