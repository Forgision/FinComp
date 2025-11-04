from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_app.core.config import settings
from fastapi_app.core.logging import get_logger
from fastapi_app.services.websocket_proxy_service import WebSocketProxyService
from fastapi_app.api.v1.dependencies import get_auth_broker
import asyncio
import os
from pathlib import Path

# Initialize logger
logger = get_logger(__name__)

# Create FastAPI app instance
app = FastAPI(
    title="OpenAlgo FastAPI",
    description="Migrated OpenAlgo application running on FastAPI.",
    version=settings.ENV_CONFIG_VERSION
)

# Get the absolute path of the project root
project_root = Path(__file__).resolve().parent.parent

@app.on_event("startup")
async def startup_event():
    """
    Log application startup, create a single instance of WebSocketProxyService,
    and attach it to the application's state.
    """
    logger.info("Application startup...")
    logger.info(f"Environment: {settings.FLASK_ENV}")
    logger.info(f"Debug mode: {settings.FLASK_DEBUG}")

    # Create the WebSocket proxy service instance and store it in the app state
    ws_proxy = WebSocketProxyService(auth_dependency=get_auth_broker)
    app.state.ws_proxy = ws_proxy

    # Mount static files
    static_dir = project_root / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        logger.info(f"Mounted static directory: {static_dir}")
    else:
        logger.warning(f"Static directory not found at {static_dir}, skipping mount.")

    # Setup Jinja2 templates
    templates_dir = project_root / "templates"
    if templates_dir.is_dir():
        templates = Jinja2Templates(directory=str(templates_dir))
        logger.info(f"Jinja2Templates: {templates}")
        # Store templates in app state to make them accessible from endpoints
        app.state.templates = templates
        logger.info(f"Jinja2Templates configured for directory: {templates_dir}")
    else:
        logger.warning(f"Templates directory not found at {templates_dir}, Jinja2 not configured.")

@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown and stop the WebSocket proxy."""
    logger.info("Application shutdown.")
    if hasattr(app.state, 'ws_proxy') and app.state.ws_proxy:
        pass

@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"status": "ok", "message": "Welcome to OpenAlgo on FastAPI!"}

# Include the API router
from fastapi_app.api.v1.api import api_router
app.include_router(api_router, prefix="/api/v1")
