from fastapi import FastAPI

from backend_app.api.routes.health import router as health_router
from backend_app.api.routes.internal import router as internal_router
from backend_app.api.routes.webhooks import router as webhooks_router
from backend_app.core.config import get_settings
from backend_app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="VPN for Clients")
app.include_router(health_router)
app.include_router(webhooks_router)
app.include_router(internal_router)
