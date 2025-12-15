import asyncio
import platform
import threading

from app.core.config import settings
from app.utils.logging import logger

# Set the correct event loop policy for Windows to avoid ZeroMQ warnings
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Global flag to track if the WebSocket server has been started
# Used to prevent multiple instances in Flask debug mode
_websocket_server_started = False
_websocket_proxy_instance = None
_websocket_thread = None


# Merge with app/web/websocket/server.py:WebSocketProxy.stop() method
def cleanup_websocket_server():
    """Clean up WebSocket server resources - cross-platform compatible"""
    global _websocket_proxy_instance, _websocket_thread

    try:
        logger.info("Cleaning up WebSocket server...")

        if _websocket_proxy_instance:
            # For Windows compatibility, set a shutdown flag instead of trying to
            # manipulate the event loop from a different thread
            _websocket_proxy_instance.running = False

            # Try to close the server gracefully
            try:
                if (
                    hasattr(_websocket_proxy_instance, "server")
                    and _websocket_proxy_instance.server
                ):
                    try:
                        _websocket_proxy_instance.server.close()
                    except Exception as e:
                        logger.warning(f"Error closing server handle: {e}")

                # Close ZMQ resources immediately
                if (
                    hasattr(_websocket_proxy_instance, "socket")
                    and _websocket_proxy_instance.socket
                ):
                    try:
                        import zmq

                        _websocket_proxy_instance.socket.setsockopt(zmq.LINGER, 0)
                        _websocket_proxy_instance.socket.close()
                    except Exception as e:
                        logger.warning(f"Error closing ZMQ socket: {e}")

                if (
                    hasattr(_websocket_proxy_instance, "context")
                    and _websocket_proxy_instance.context
                ):
                    try:
                        _websocket_proxy_instance.context.term()
                    except Exception as e:
                        logger.warning(f"Error terminating ZMQ context: {e}")

            except Exception as e:
                logger.error(f"Error during WebSocket cleanup: {e}")
            finally:
                _websocket_proxy_instance = None

        if _websocket_thread and _websocket_thread.is_alive():
            logger.info("Waiting for WebSocket thread to finish...")
            _websocket_thread.join(timeout=3.0)  # Reduced timeout for faster shutdown
            if _websocket_thread.is_alive():
                logger.warning("WebSocket thread did not finish gracefully")
            _websocket_thread = None

        logger.info("WebSocket server cleanup completed")

    except Exception as e:
        logger.error(f"Error during WebSocket cleanup: {e}")
        # Last resort: force cleanup
        _websocket_proxy_instance = None
        _websocket_thread = None


# Merge with app/web/websocket/server.py:WebSocketProxy.start() method
def start_websocket_server():
    """
    Start the WebSocket proxy server in a separate thread.
    This function should be called when the Flask app starts.
    """
    global _websocket_proxy_instance, _websocket_thread

    logger.info("Starting WebSocket proxy server in a separate thread")

    def run_websocket_server():
        """Run the WebSocket server in an event loop"""
        global _websocket_proxy_instance
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Import here to avoid circular imports
            from app.web.websocket.server import WebSocketProxy

            ws_host = settings.WEBSOCKET_HOST
            ws_port = settings.WEBSOCKET_PORT

            # Create and store the proxy instance
            _websocket_proxy_instance = WebSocketProxy(host=ws_host, port=ws_port)

            # Start the proxy
            loop.run_until_complete(_websocket_proxy_instance.start())

        except Exception as e:
            logger.exception(f"Error in WebSocket server thread: {e}")
            _websocket_proxy_instance = None

    # Start the WebSocket server in a daemon thread
    _websocket_thread = threading.Thread(
        target=run_websocket_server,
        daemon=False,  # Changed to False so we can properly clean up
    )
    _websocket_thread.start()

    logger.info("WebSocket proxy server thread started")
    return _websocket_thread


# --- Data Service ---
_data_service_task = None
_data_service_instance = None


def cleanup_data_service():
    """Clean up DataService resources"""
    global _data_service_instance, _data_service_task

    try:
        logger.info("Cleaning up DataService...")
        if _data_service_instance:
            asyncio.create_task(_data_service_instance.stop())
            _data_service_instance = None

        if _data_service_task:
            _data_service_task.cancel()
            _data_service_task = None

        logger.info("DataService cleanup completed")
    except Exception as e:
        logger.error(f"Error during DataService cleanup: {e}")


def start_data_service():
    """Start DataService as a background task"""
    global _data_service_instance, _data_service_task

    try:
        logger.info("Starting DataService...")
        from app.data.service import DataService

        # Phase 1: DataService runs as SERVER in the background task
        _data_service_instance = DataService(mode="SERVER")
        _data_service_task = asyncio.create_task(_data_service_instance.start())
        logger.info("DataService started")
    except Exception as e:
        logger.error(f"Failed to start DataService: {e}")


# --- Algo Service ---
_algo_service_task = None
_algo_service_instance = None


def cleanup_algo_service():
    """Clean up AlgoService resources"""
    global _algo_service_instance, _algo_service_task

    try:
        logger.info("Cleaning up AlgoService...")
        if _algo_service_instance:
            asyncio.create_task(_algo_service_instance.stop())
            _algo_service_instance = None

        if _algo_service_task:
            _algo_service_task.cancel()
            _algo_service_task = None

        logger.info("AlgoService cleanup completed")
    except Exception as e:
        logger.error(f"Error during AlgoService cleanup: {e}")


def start_algo_service():
    """Start AlgoService as a background task"""
    global _algo_service_instance, _algo_service_task

    try:
        logger.info("Starting AlgoService...")
        from app.algo.service import AlgoService

        _algo_service_instance = AlgoService()
        _algo_service_task = asyncio.create_task(_algo_service_instance.start())
        logger.info("AlgoService started")
    except Exception as e:
        logger.error(f"Failed to start AlgoService: {e}")


# --- Execution Service ---
_execution_service_task = None
_execution_service_instance = None


def cleanup_execution_service():
    """Clean up ExecutionService resources"""
    global _execution_service_instance, _execution_service_task

    try:
        logger.info("Cleaning up ExecutionService...")
        if _execution_service_instance:
            asyncio.create_task(_execution_service_instance.stop())
            _execution_service_instance = None

        if _execution_service_task:
            _execution_service_task.cancel()
            _execution_service_task = None

        logger.info("ExecutionService cleanup completed")
    except Exception as e:
        logger.error(f"Error during ExecutionService cleanup: {e}")


def start_execution_service():
    """Start ExecutionService as a background task"""
    global _execution_service_instance, _execution_service_task

    try:
        logger.info("Starting ExecutionService...")
        from app.core.execution.service import ExecutionService

        _execution_service_instance = ExecutionService()
        _execution_service_task = asyncio.create_task(_execution_service_instance.start())
        logger.info("ExecutionService started")
    except Exception as e:
        logger.error(f"Failed to start ExecutionService: {e}")
