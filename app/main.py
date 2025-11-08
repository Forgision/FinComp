from contextlib import asynccontextmanager
from typing import cast # Added import

import socketio
from app.web.frontend import templates
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse, Response # Ensure Response is imported
from fastapi_csrf_protect.exceptions import CsrfProtectError
# from fastapi_csrf_protect.flexible import CsrfProtect
from pydantic import BaseModel
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles

from app.core.schemas import initizing_databases
from app.core.config import settings
from app.utils.logging import logger
from app.core.middleware import TrafficLoggerMiddleware # Updated import
from app.core.services.limiter_service import limiter
from app.utils.web.socketio import sio
from app.web.frontend.routes.analyzer import analyzer_router
from app.web.frontend.routes.apikey import apikey_router
from app.web.frontend.routes.auth import auth_router
from app.web.frontend.routes.broker_auth import broker_router
from app.web.frontend.routes.chartink import chartink_router
from app.web.frontend.routes.core import core_router
from app.web.frontend.routes.dashboard import dashboard_router
from app.web.frontend.routes.latency import latency_router
from app.web.frontend.routes.log import log_router
from app.web.backend.api.master_contract_status import master_contract_status_router
from app.web.backend.api.orders import orders_router
from app.web.frontend.routes.pnltracker import pnltracker_router
from app.web.frontend.routes.python_strategy import python_strategy_router
from app.web.frontend.routes.sandbox import sandbox_router
from app.web.frontend.routes.search import search_router
from app.web.frontend.routes.security import security_router
from app.web.frontend.routes.settings import settings_router
from app.web.frontend.routes.strategy import strategy_router
from app.web.backend.api.telegram import telegram_router
from app.web.frontend.routes.traffic import traffic_router
from app.web.frontend.routes.tv_json import tv_json_router
from app.web.frontend.routes.websocket import websocket_router
# from app.web.backend.api.monitoring import monitoring_router
from app.web.websocket.fastapi_integration import (
    cleanup_websocket_server,
    start_websocket_server,
)
from app.web.websocket.broker_factory import register_all_adapters
from app.core.models.error_models import BaseErrorResponse
from app.web.backend.middleware import CorrelationIdMiddleware

# from app.utils.plugin_loader import load_broker_auth_functions

class CsrfSettings(BaseModel):
    secret_key: str = settings.APP_KEY
    cookie_samesite: str = "none"
    cookie_secure: bool = True
    # cookie_key: str = 'csrf_token'
    token_key: str = 'csrf_token'

# @CsrfProtect.load_config
# def get_csrf_config():
#     return CsrfSettings()


async def setup_environment():
    """Initializes the application environment, database, and plugins."""
    logger.info("Starting environment setup...")
    await initizing_databases()
    # load_broker_auth_functions()
    # ensure_auth_tables_exists()
    # ensure_user_tables_exists()
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
    await setup_environment()
    start_websocket_server()
    separate_str = "=" * 60
    logger.info(separate_str)
    logger.info("OpenAlgo FastAPI is running!")
    logger.info(f"Access the application at: http://{settings.APP_HOST_IP}:{settings.APP_PORT}")
    logger.info(separate_str)
    logger.info("Application startup complete.")
    yield
    cleanup_websocket_server()

_app = FastAPI(debug=settings.APP_DEBUG, lifespan=lifespan)
_app.state.limiter = limiter

# Wrapper to make _rate_limit_exceeded_handler compatible with FastAPI's ExceptionHandler type
async def _fastapi_compatible_rate_limit_handler(request: Request, exc: Exception) -> Response:
    # We know that when this handler is invoked for RateLimitExceeded, exc will be of that type.
    # The type checker is being strict about the declared type in the function signature.
    return _rate_limit_exceeded_handler(request, cast(RateLimitExceeded, exc))

_app.add_exception_handler(RateLimitExceeded, _fastapi_compatible_rate_limit_handler)

# Mount static files
_app.mount("/static", StaticFiles(directory="app/web/frontend/static"), name="static")

# add templete
templates.env.globals['url_for'] = _app.url_path_for

# Apply Session Middleware
_app.add_middleware(CorrelationIdMiddleware)
_app.add_middleware(SessionMiddleware, secret_key=settings.APP_KEY)

# Register routers
_app.include_router(auth_router)
_app.include_router(broker_router)
_app.include_router(core_router, tags=["core"])
_app.include_router(dashboard_router, tags=["dashboard"])
_app.include_router(orders_router, prefix="/api/v1/orders", tags=["Orders"])
_app.include_router(telegram_router, prefix="/api/v1/telegram", tags=["Telegram"])
_app.include_router(analyzer_router, prefix="/analyzer", tags=["analyzer"])
_app.include_router(apikey_router, tags=["apikey"])
_app.include_router(chartink_router, prefix="/chartink", tags=["chartink"])
_app.include_router(latency_router, prefix="/latency", tags=["latency"])
_app.include_router(log_router, prefix="/logs", tags=["logs"])
_app.include_router(master_contract_status_router)
_app.include_router(pnltracker_router)
_app.include_router(python_strategy_router)
_app.include_router(sandbox_router)
_app.include_router(search_router)
_app.include_router(security_router)
_app.include_router(settings_router)
_app.include_router(strategy_router)
_app.include_router(traffic_router)
_app.include_router(tv_json_router)
_app.include_router(websocket_router)
# _app.include_router(monitoring_router)
register_all_adapters()


@_app.get("/test")
async def test():
    return {"message": "Hello World"}

@_app.get("/")
async def root(request: Request):
    if 'user' not in request.session or not request.session.get('logged_in'):
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

@_app.exception_handler(CsrfProtectError)
def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

# Add rate limit exception handler
@_app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Rate limit exceeded"}
    )

@_app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        content = BaseErrorResponse(
            message="Rate limit exceeded. Please try again later.",
            code="RATE_LIMIT_EXCEEDED",
            details=None
        ).model_dump()
    else:
        # Ensure detail is a dictionary for BaseErrorResponse, if it's not already
        if isinstance(exc.detail, dict):
            content = exc.detail
        else:
            content = BaseErrorResponse(
                message=exc.detail,
                code=f"HTTP_{exc.status_code}", # Provide a default code
                details=None # Provide default details
            ).model_dump()

    return JSONResponse(
        status_code=exc.status_code,
        content=content
    )

_app.add_middleware(TrafficLoggerMiddleware)

app = socketio.ASGIApp(sio, _app)
