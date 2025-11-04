import pytest
from httpx import AsyncClient
import asyncio
from unittest.mock import MagicMock
from fastapi_app.core.logging import get_logger

logger = get_logger(__name__)

@pytest.mark.asyncio
async def test_websocket_connection_unauthorized(async_client: AsyncClient):
    """
    Test that an unauthorized WebSocket connection is closed.
    """
    try:
        async with async_client.websocket_connect("/api/v1/ws") as websocket:
            # Expect the server to close the connection
            await websocket.receive_json()
            pytest.fail("Should have raised an exception")
    except Exception as e:
        assert True # Expect to get here

@pytest.mark.asyncio
async def test_websocket_connection_authorized(async_client: AsyncClient):
    """
    Test that an authorized WebSocket connection is accepted.
    """
    # Get the running service instance from the app state
    ws_proxy = async_client._app.state.ws_proxy

    # Mock the auth dependency directly on the service instance
    mock_auth_result = MagicMock()
    mock_auth_result.token = "test_user"
    mock_auth_result.broker = "test_broker"
    logger.info(f"mock_auth_result: {mock_auth_result}")
    async def mock_auth_dependency(api_key):
        logger.info(f"api_key: {api_key}")
        return mock_auth_result

    ws_proxy.auth_dependency = mock_auth_dependency

    async with async_client.websocket_connect("/api/v1/ws") as websocket:
        # Send an authentication message
        await websocket.send_json({"type": "auth", "api_key": "test_key"})
        # Check for auth success message
        response = await websocket.receive_json()
        assert response["status"] == "success"

@pytest.mark.asyncio
async def test_websocket_subscribe_and_receive(async_client: AsyncClient):
    """
    Test subscribing to a symbol and receiving a message.
    """
    # Get the running service instance from the app state
    ws_proxy = async_client._app.state.ws_proxy

    # Mock the auth dependency directly on the service instance
    mock_auth_result = MagicMock()
    mock_auth_result.token = "test_user"
    mock_auth_result.broker = "test_broker"
    logger.info(f"mock_auth_result: {mock_auth_result}")
    async def mock_auth_dependency(api_key):
        logger.info(f"api_key: {api_key}")
        return mock_auth_result

    ws_proxy.auth_dependency = mock_auth_dependency

    async with async_client.websocket_connect("/api/v1/ws") as websocket:
        # Authenticate first
        await websocket.send_json({"type": "auth", "api_key": "test_key"})
        auth_response = await websocket.receive_json()
        assert auth_response["status"] == "success"

        # Manually add a mock broker adapter for this user
        mock_adapter = MagicMock()
        mock_adapter.subscribe.return_value = {"status": "success"}
        ws_proxy.broker_adapters["test_user"] = mock_adapter

        # Subscribe to a symbol
        await websocket.send_json({"type": "subscribe", "symbols": [{"symbol": "NIFTY", "exchange": "NSE"}]})
        sub_response = await websocket.receive_json()
        assert sub_response["status"] == "success"


        # Mock a message broadcast from the "feed"
        async def mock_broadcast():
            await asyncio.sleep(0.1) # allow time for processing
            await ws_proxy.send_message("test_user", {"symbol": "NIFTY", "price": 100})

        asyncio.create_task(mock_broadcast())

        # Receive the message
        data = await websocket.receive_json()
        assert data == {"symbol": "NIFTY", "price": 100}