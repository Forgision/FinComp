import os
import subprocess
import sys
import signal
import atexit
import argparse
import platform
import stat

def cleanup():
    """
    Cleans up background processes when the script exits.
    Note: The WebSocket proxy is now managed by FastAPI's lifespan events.
    This cleanup function is primarily for processes started directly by this script.
    """
    print("[OpenAlgo] Shutting down...")
    # No direct cleanup needed for websocket_proxy_process here as it's managed by FastAPI.
    # This function is kept for general cleanup if other background processes were to be added.

def setup_signal_handlers():
    """
    Sets up signal handlers for graceful shutdown.
    The actual cleanup is deferred to the atexit handler.
    """
    def signal_handler(sig, frame):
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def create_directories():
    """
    Creates necessary directories for the application.
    """
    print("[OpenAlgo] Creating directories...")
    dirs = ['db', 'log', 'log/strategies', 'strategies', 'strategies/scripts', 'keys']
    for d in dirs:
        try:
            os.makedirs(d, exist_ok=True)
        except OSError as e:
            print(f"⚠️  Could not create directory {d}: {e}")

def set_permissions():
    """
    Sets permissions for directories, skipping on Windows.
    """
    if platform.system() == "Windows":
        print("ℹ️  Skipping permission setup on Windows.")
        return

    if not os.access('.', os.W_OK):
        print("⚠️  Running with restricted permissions (current directory not writable).")
        return

    print("[OpenAlgo] Setting directory permissions...")
    try:
        # Set permissions for general directories (rwxr-xr-x)
        for d in ['db', 'log', 'strategies']:
            if os.path.isdir(d):
                for dirpath, _, filenames in os.walk(d):
                    os.chmod(dirpath, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)  # 755
                    for filename in filenames:
                        os.chmod(os.path.join(dirpath, filename), stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)  # 644
    except OSError as e:
        print(f"⚠️  Skipping chmod for general directories (may be mounted volume or permission restricted): {e}")

    try:
        # Set restrictive permissions for keys directory (rwx------)
        if os.path.isdir('keys'):
            os.chmod('keys', stat.S_IRWXU)  # 700
    except OSError as e:
        print(f"⚠️  Failed to set permissions for 'keys' directory: {e}")


def start_uvicorn_app():
    """
    Starts the main FastAPI application using Uvicorn.
    """
    print("[OpenAlgo] Starting FastAPI application on port 8000...")
    try:
        uvicorn_command = [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload" # Enable auto-reloading for development
        ]
        uvicorn_process = subprocess.Popen(uvicorn_command)
        uvicorn_process.wait()
    except FileNotFoundError:
        print("❌ ERROR: 'uvicorn' command not found. Make sure Uvicorn is installed in your environment.")
    except Exception as e:
        print(f"❌ ERROR: Failed to start Uvicorn: {e}")

def main():
    """
    Main function to orchestrate the application startup.
    """
    parser = argparse.ArgumentParser(description="OpenAlgo Startup Script")
    parser.add_argument("--debug", action="store_true", help="Run the application in debug mode.")
    args = parser.parse_args()

    print("[OpenAlgo] Starting up...")

    atexit.register(cleanup)
    setup_signal_handlers()

    create_directories()
    set_permissions()
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

    # The WebSocket proxy is now managed by FastAPI's lifespan events.
    # No need to start it separately here.

    start_uvicorn_app() # Always start with Uvicorn for FastAPI

if __name__ == "__main__":
    main()