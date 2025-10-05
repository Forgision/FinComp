import sys
import os

# Add the project root to the Python path for development environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.core.config import settings
from app.core.middleware import CSPMiddleware, SecurityMiddleware, TrafficLoggingMiddleware
import asyncio
import subprocess
import signal

# from app.db.session import init_db
from app.api.v1 import api_router as api_v1_router
from services.telegram_bot_service import telegram_bot_service
from database.telegram_db import get_bot_config # Import get_bot_config directly

websocket_proxy_process = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Application startup
    print("FastAPI application startup completed.")
    
    # Start WebSocket proxy server
    global websocket_proxy_process
    print("[OpenAlgo] Starting WebSocket proxy server on port 8765...")
    try:
        command = [sys.executable, "-m", "websocket_proxy.server"]
        websocket_proxy_process = subprocess.Popen(command)
        print(f"[OpenAlgo] WebSocket proxy server started with PID {websocket_proxy_process.pid}")
    except FileNotFoundError:
        print("❌ ERROR: Could not find 'websocket_proxy.server'. Make sure it's installed and in your PYTHONPATH.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: Failed to start websocket proxy server: {e}")
        sys.exit(1)

    # Start Telegram Bot
    config = get_bot_config() # Call get_bot_config as a standalone function
    if config and config.get('bot_token'):
        print("[OpenAlgo] Initializing Telegram bot...")
        success, message = await telegram_bot_service.initialize_bot(token=config['bot_token'])
        if success:
            print(f"[OpenAlgo] Telegram bot initialized: {message}")
            telegram_bot_service.start_bot() # This starts the bot in a new thread
            print("[OpenAlgo] Telegram bot started.")
        else:
            print(f"❌ ERROR: Failed to initialize Telegram bot: {message}")
    else:
        print("[OpenAlgo] Telegram bot token not configured. Skipping bot startup.")

    yield
    # Application shutdown
    print("FastAPI application shutdown completed.")
    
    # Shutdown WebSocket proxy server
    if websocket_proxy_process and websocket_proxy_process.poll() is None:
        print(f"[OpenAlgo] Terminating WebSocket proxy server with PID {websocket_proxy_process.pid}...")
        websocket_proxy_process.terminate()
        try:
            websocket_proxy_process.wait(timeout=5)
            print("[OpenAlgo] WebSocket proxy server shut down.")
        except subprocess.TimeoutExpired:
            print(f"[OpenAlgo] WebSocket proxy server with PID {websocket_proxy_process.pid} did not terminate in time. Killing it.")
            websocket_proxy_process.kill()
    else:
        print("[OpenAlgo] WebSocket proxy server was not running.")

    # Stop Telegram Bot
    if telegram_bot_service.is_running:
        print("[OpenAlgo] Stopping Telegram bot...")
        telegram_bot_service.stop_bot()
        print("[OpenAlgo] Telegram bot stopped.")

def create_app():
    app = FastAPI(
        title="OpenAlgo FastAPI",
        description="FastAPI backend for OpenAlgo algorithmic trading platform",
        version="0.1.0",
        lifespan=lifespan
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Adjust as per your frontend URL
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted Host Middleware
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=[settings.HOST_SERVER.split('//')[-1].split(':')[0], "localhost", "127.0.0.1"]
    )

    # Session Middleware (for CSRF protection and session management)
    app.add_middleware(
        SessionMiddleware, secret_key=settings.APP_KEY
    )

    # Custom Middleware
    app.add_middleware(CSPMiddleware)
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(TrafficLoggingMiddleware)

    # Include API routers
    app.include_router(api_v1_router, prefix="/api/v1")
    
    # Serve static files
    app.mount("/static", StaticFiles(directory="app/frontend/static"), name="static")

    # Configure Jinja2 templates
    templates = Jinja2Templates(directory="app/frontend/templates")
    app.state.templates = templates

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)