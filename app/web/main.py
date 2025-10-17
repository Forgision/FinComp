import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import socketio
from starlette.responses import Response
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi_csrf_protect.flexible import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.staticfiles import StaticFiles # Import StaticFiles
from app.core.config import settings
from app.utils.logging import logger
from ..utils.web import limiter
from ..utils.web.security import SecurityHeadersMiddleware, CSRFMiddleware
from .backend.routes import auth_router, broker_router, dashboard_router, analyzer_router, apikey_router, chartink_router, latency_router, log_router, master_contract_status_router, orders_router, pnltracker_router, python_strategy_router, sandbox_router, search_router, security_router, settings_router, strategy_router, telegram_router, traffic_router, tv_json_router, websocket_router
from .backend.routes.core import core_router as core_router
from .frontend import templates
from app.utils.web.socketio import sio
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

_app = FastAPI(debug=settings.APP_DEBUG, lifespan=lifespan)
_app.state.limiter = limiter
_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files
_app.mount("/static", StaticFiles(directory=settings.BASE_DIR / "web/frontend/static"), name="static")

# add templete
templates.env.globals['url_for'] = _app.url_path_for

# Apply CORS middleware if enabled
# if settings.CORS_ENABLED:
#     _app.add_middleware(
#         CORSMiddleware,
#         allow_origins=[origin.strip() for origin in settings.CORS_ALLOWED_ORIGINS.split(',')] if settings.CORS_ALLOWED_ORIGINS else [],
#         allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
#         allow_methods=[method.strip() for method in settings.CORS_ALLOWED_METHODS.split(',')] if settings.CORS_ALLOWED_METHODS else [],
#         allow_headers=[header.strip() for header in settings.CORS_ALLOWED_HEADERS.split(',')] if settings.CORS_ALLOWED_HEADERS else [],
#         expose_headers=[header.strip() for header in settings.CORS_EXPOSED_HEADERS.split(',')] if settings.CORS_EXPOSED_HEADERS else [],
#         max_age=settings.CORS_MAX_AGE,
#     )

# Apply Session Middleware
_app.add_middleware(SessionMiddleware, secret_key=settings.APP_KEY)

# # Apply Security Headers middleware
# _app.add_middleware(SecurityHeadersMiddleware)

# Apply CSRF middleware if enabled
# if settings.CSRF_ENABLED:
#     _app.add_middleware(
#         CSRFMiddleware
#     )

# Register routers
_app.include_router(auth_router)
_app.include_router(broker_router)
_app.include_router(core_router, tags=["core"])
# _app.include_router(root_router, tags=["web"])
_app.include_router(dashboard_router, tags=["dashboard"])
_app.include_router(orders_router, prefix="/api/v1/orders", tags=["Orders"])
_app.include_router(telegram_router, prefix="/api/v1/telegram", tags=["Telegram"])
_app.include_router(analyzer_router, tags=["analyzer"])
_app.include_router(apikey_router, tags=["apikey"])
_app.include_router(chartink_router, tags=["chartink"])
_app.include_router(latency_router, tags=["latency"])
_app.include_router(log_router, tags=["logs"])
_app.include_router(master_contract_status_router)
_app.include_router(orders_router)
_app.include_router(pnltracker_router)
_app.include_router(python_strategy_router)
_app.include_router(sandbox_router)
_app.include_router(search_router)
_app.include_router(security_router)
_app.include_router(settings_router)
_app.include_router(strategy_router)
_app.include_router(telegram_router)
_app.include_router(traffic_router)
_app.include_router(tv_json_router)
_app.include_router(websocket_router)
#Following are from app/web/backend/api
# _app.include_router(account_router, prefix="/api/v1/account", tags=["Account"])
# _app.include_router(market_data_router, prefix="/api/v1/data", tags=["Market Data"])
# _app.include_router(utility_router, prefix="/api/v1/utility", tags=["Utility"])


@_app.get("/test")
async def test():
    return {"message": "Hello World"}

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
    if exc.status_code == 429:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                'status': 'error',
                'message': 'Rate limit exceeded. Please try again later.'
            }
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail}
    )

# @app.get("/favicon.ico", include_in_schema=False)
# async def get_favicon():
#     return Response(status_code=204)

# @app.get("/config")
# def get_config():
#     return settings.model_dump()

app = socketio.ASGIApp(sio, _app)
