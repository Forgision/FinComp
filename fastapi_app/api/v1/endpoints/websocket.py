from fastapi import APIRouter, WebSocket

from fastapi_app.core.logging import get_logger
from fastapi_app.services.websocket_proxy_service import WebSocketProxyService

logger = get_logger(__name__)

router = APIRouter()

# This endpoint acts as the entry point for WebSocket connections.
# It retrieves the running instance of the WebSocketProxyService from the app's state
# (where it's initialized in `main.py`) and hands off the connection to the
# service's dedicated client handler.

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Handles incoming WebSocket connections and passes them to the WebSocketProxyService.
    The service's `handle_client` method will then manage the entire lifecycle of this
    specific client connection, including authentication, message processing, and cleanup.
    """
    # Retrieve the singleton instance of the WebSocketProxyService from the app's state.
    ws_proxy: WebSocketProxyService = websocket.scope['app'].state.ws_proxy

    # Delegate the handling of the entire client lifecycle to the service.
    # This mimics the behavior of `websockets.serve(self.handle_client, ...)`
    # where the handler function is called for each new connection.
    await ws_proxy.handle_fastapi_websocket(websocket)
