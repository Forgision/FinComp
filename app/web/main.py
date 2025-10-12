import os

from fastapi import FastAPI
from starlette.responses import Response
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

from starlette.staticfiles import StaticFiles # Import StaticFiles
from app.core.config import settings
# from ..utils.logger import log_startup_banner
# from app.utils.logging import setup_logging, get_logger, log_startup_banner
from app.utils.logging import logger
from ..utils.web.security import SecurityHeadersMiddleware, CSRFMiddleware
from .backend.api import auth_router, broker_router, core_router, dashboard_router


# Setup logging as early as possible
# setup_logging()
# logger = get_logger(__name__)

app = FastAPI(debug=settings.APP_DEBUG)

# Mount static files
app.mount("/static", StaticFiles(directory=settings.BASE_DIR / "web/frontend/static"), name="static")

# add templete
# templates = Jinja2Templates(directory=os.path.join(settings.BASE_DIR, "web/frontend/templates"))

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

# # Apply CSRF middleware if enabled
# if settings.CSRF_ENABLED:
#     app.add_middleware(
#         CSRFMiddleware
#     )

# Register routers
app.include_router(auth_router)
app.include_router(broker_router, prefix="/auth/broker", tags=["broker"])
app.include_router(core_router, tags=["core"])
# app.include_router(root_router, tags=["web"])
app.include_router(dashboard_router, tags=["dashboard"])

@app.on_event("startup")
async def startup_event():
    # Log startup banner
    # log_startup_banner(logger, "OpenAlgo FastAPI is running!", f"http://{settings.APP_HOST_IP}:{settings.APP_PORT}")
    separate_str = "=" * 60
    logger.info(separate_str)
    logger.info("OpenAlgo FastAPI is running!")
    logger.info(f"Access the application at: http://{settings.APP_HOST_IP}:{settings.APP_PORT}")
    logger.info(separate_str)
    logger.info("Application startup complete.")

@app.get("/test")
async def test():
    return {"message": "Hello World"}

# @app.get("/favicon.ico", include_in_schema=False)
# async def get_favicon():
#     return Response(status_code=204)

# @app.get("/config")
# def get_config():
#     return settings.model_dump()
