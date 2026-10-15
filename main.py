from fastapi import FastAPI

from src.api.routes.base import router as base_router
from src.api.routes.health import router as health_router

app = FastAPI(title="DocSummary")

app.include_router(base_router)
app.include_router(health_router)