import logging

from fastapi import APIRouter, FastAPI

from app.config import get_settings
from app.errors import register_error_handlers
from app.modules.admin.router import router as admin_router
from app.modules.agent.router import router as agent_router
from app.modules.auth.router import router as auth_router
from app.modules.conversations.router import router as conversations_router
from app.modules.health.router import router as health_router

settings = get_settings()
logging.basicConfig(level=settings.log_level)
# Never log request bodies: uvicorn access logs only contain the method, path and status.

app = FastAPI(
    title="Orienta API",
    version="0.1.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
)
register_error_handlers(app)

api = APIRouter(prefix="/api/v1")
for router in (health_router, auth_router, conversations_router, agent_router, admin_router):
    api.include_router(router)
app.include_router(api)
