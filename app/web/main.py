import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.responses import Response
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi_csrf_protect.flexible import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.staticfiles import StaticFiles # Import StaticFiles
from app.core.config import settings
# from ..utils.logger import log_startup_banner
# from app.utils.logging import setup_logging, get_logger, log_startup_banner
from app.utils.logging import logger
from ..utils.web import limiter
from ..utils.web.security import SecurityHeadersMiddleware, CSRFMiddleware
from .backend.api import auth_router, broker_router, core_router, dashboard_router
from .frontend import templates
from app.utils.web.socketio import socket_app
from app.web.websocket.fastapi_integration import start_websocket_server, cleanup_websocket_server

from app.db.auth_db import init_db as ensure_auth_tables_exists
from app.db.user_db import init_db as ensure_user_tables_exists
# from app.db.symbol import init_db as ensure_master_contract_tables_exists
# from app.db.apilog_db import init_db as ensure_api_log_tables_exists
# from app.db.analyzer_db import init_db as ensure_analyzer_tables_exists
# from app.db.settings_db import init_db as ensure_settings_tables_exists
# from app.db.chartink_db import init_db as ensure_chartink_tables_exists
# from app.db.traffic_db import init_logs_db as ensure_traffic_logs_exists
# from app.db.latency_db import init_latency_db as ensure_latency_tables_exists
# from app.db.strategy_db import init_db as ensure_strategy_tables_exists
# from app.db.sandbox_db import init_db as ensure_sandbox_tables_exists
# from app.utils.plugin_loader import load_broker_auth_functions

class CsrfSettings(BaseModel):
    secret_key: str = settings.APP_KEY
    cookie_samesite: str = "none"
    cookie_secure: bool = True
    # cookie_key: str = 'csrf_token'
    token_key: str = 'csrf_token'

@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()


def setup_environment():
    """Initializes the application environment, database, and plugins."""
    logger.info("Starting environment setup...")
    # load_broker_auth_functions()
    ensure_auth_tables_exists()
    ensure_user_tables_exists()
    # ensure_master_contract_tables_exists()
    # ensure_api_log_tables_exists()
    # ensure_analyzer_tables_exists()
    # ensure_settings_tables_exists()
    # ensure_chartink_tables_exists()
    # ensure_traffic_logs_exists()
    # ensure_latency_tables_exists()
    # ensure_strategy_tables_exists()
    # ensure_sandbox_tables_exists()
    logger.info("Environment setup completed successfully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    """
    setup_environment()
    start_websocket_server()
    separate_str = "=" * 60
    logger.info(separate_str)
    logger.info("OpenAlgo FastAPI is running!")
    logger.info(f"Access the application at: http://{settings.APP_HOST_IP}:{settings.APP_PORT}")
    logger.info(separate_str)
    logger.info("Application startup complete.")
    yield
    cleanup_websocket_server()

app = FastAPI(debug=settings.APP_DEBUG, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files
app.mount("/static", StaticFiles(directory=settings.BASE_DIR / "web/frontend/static"), name="static")

# Mount Socket.IO app
app.mount("/ws", socket_app)

# add templete
templates.env.globals['url_for'] = app.url_path_for

# Apply CORS middleware if enabled
# if settings.CORS_ENABLED:
#     app.add_middleware(
#         CORSMiddleware,
#         allow_origins=[origin.strip() for origin in settings.CORS_ALLOWED_ORIGINS.split(',')] if settings.CORS_ALLOWED_ORIGINS else [],
#         allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
#         allow_methods=[method.strip() for method in settings.CORS_ALLOWED_METHODS.split(',')] if settings.CORS_ALLOWED_METHODS else [],
#         allow_headers=[header.strip() for header in settings.CORS_ALLOWED_HEADERS.split(',')] if settings.CORS_ALLOWED_HEADERS else [],
#         expose_headers=[header.strip() for header in settings.CORS_EXPOSED_HEADERS.split(',')] if settings.CORS_EXPOSED_HEADERS else [],
#         max_age=settings.CORS_MAX_AGE,
#     )

# Apply Session Middleware
app.add_middleware(SessionMiddleware, secret_key=settings.APP_KEY)

# # Apply Security Headers middleware
# app.add_middleware(SecurityHeadersMiddleware)

# Apply CSRF middleware if enabled
# if settings.CSRF_ENABLED:
#     app.add_middleware(
#         CSRFMiddleware
#     )

# Register routers
app.include_router(auth_router)
app.include_router(broker_router)
app.include_router(core_router, tags=["core"])
# app.include_router(root_router, tags=["web"])
app.include_router(dashboard_router, tags=["dashboard"])


@app.get("/test")
async def test():
    return {"message": "Hello World"}

@app.exception_handler(CsrfProtectError)
def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

# Add rate limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Rate limit exceeded"}
    )

# @app.get("/favicon.ico", include_in_schema=False)
# async def get_favicon():
#     return Response(status_code=204)

# @app.get("/config")
# def get_config():
#     return settings.model_dump()
