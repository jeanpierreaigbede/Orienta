import logging

from fastapi import APIRouter, FastAPI

from app.config import get_settings
from app.errors import register_error_handlers
from app.modules.health.router import router as health_router

settings = get_settings()
logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="Orienta API",
    version="0.1.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
)
register_error_handlers(app)

api = APIRouter(prefix="/api/v1")
api.include_router(health_router)
app.include_router(api)
