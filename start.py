import os
import subprocess
import sys
import signal
import atexit
import argparse
import platform
import stat

# Global variable to hold the websocket proxy process
websocket_proxy_process = None

def cleanup():
    """
    Cleans up background processes when the script exits.
    """
    global websocket_proxy_process
    print("[OpenAlgo] Shutting down...")
    if websocket_proxy_process and websocket_proxy_process.poll() is None:
        print(f"[OpenAlgo] Terminating WebSocket proxy server with PID {websocket_proxy_process.pid}...")
        websocket_proxy_process.terminate()
        try:
            # Wait for a short period for the process to terminate
            websocket_proxy_process.wait(timeout=5)
            print("[OpenAlgo] WebSocket proxy server shut down.")
        except subprocess.TimeoutExpired:
            print(f"[OpenAlgo] WebSocket proxy server with PID {websocket_proxy_process.pid} did not terminate in time. Killing it.")
            websocket_proxy_process.kill()
            print("[OpenAlgo] WebSocket proxy server killed.")
    else:
        print("[OpenAlgo] WebSocket proxy server was not running.")

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

def start_websocket_proxy():
    """
    Starts the WebSocket proxy server in a background process.
    """
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

def start_gunicorn_app():
    """
    Starts the main application using Gunicorn.
    """
    print("[OpenAlgo] Starting application on port 5000 with eventlet...")
    try:
        gunicorn_command = [
            "gunicorn",
            "--worker-class", "eventlet",
            "--workers", "1",
            "--bind", "0.0.0.0:5000",
            "--timeout", "120",
            "--graceful-timeout", "30",
            "--log-level", "warning",
            "app:app"
        ]
        gunicorn_process = subprocess.Popen(gunicorn_command)
        gunicorn_process.wait()
    except FileNotFoundError:
        print("❌ ERROR: 'gunicorn' command not found. Make sure Gunicorn is installed in your environment.")
    except Exception as e:
        print(f"❌ ERROR: Failed to start Gunicorn: {e}")

def start_debug_app():
    """
    Starts the Flask application in debug mode.
    """
    print("[OpenAlgo] Starting application in DEBUG MODE on port 5000...")
    try:
        from app import app
        # The Flask dev server will handle its own lifecycle, including reloading.
        # The proxy is started once and will persist through reloads.
        app.run(host="0.0.0.0", port=5000, debug=True)
    except ImportError:
        print("❌ ERROR: Could not import 'app' from 'app'. Make sure 'app.py' exists and is in the PYTHONPATH.")
    except Exception as e:
        print(f"❌ ERROR: Failed to start debug server: {e}")

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

    # Start the websocket proxy as a separate, long-running service.
    start_websocket_proxy()

    if args.debug:
        start_debug_app()
    else:
        start_gunicorn_app()

if __name__ == "__main__":
    main()