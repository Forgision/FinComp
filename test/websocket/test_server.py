import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.web.websocket.server import WebSocketProxy

@pytest.fixture
def proxy():
    return WebSocketProxy()

@pytest.mark.asyncio
@patch('app.web.websocket.websocket.server.verify_api_key', return_value="test_user")
@patch('app.web.websocket.websocket.server.get_broker_name', return_value="finvasia")
@patch('app.web.websocket.websocket.server.create_broker_adapter')
async def test_authenticate_client_success(mock_create_broker_adapter, mock_get_broker_name, mock_verify_api_key, proxy):
    mock_adapter = MagicMock()
    mock_adapter.initialize.return_value = {"success": True}
    mock_adapter.connect.return_value = {"success": True}
    mock_create_broker_adapter.return_value = mock_adapter

    client_id = 12345
    proxy.clients[client_id] = AsyncMock()

    await proxy.authenticate_client(client_id, {"api_key": "test_api_key"})
    assert proxy.clients[client_id].send.call_count == 1
    # Further assertions can be made on the content of the sent message


@pytest.mark.asyncio
async def test_process_client_message_invalid_json(proxy):
    client_id = 12345
    proxy.clients[client_id] = AsyncMock()

    await proxy.process_client_message(client_id, "invalid json")
    assert proxy.clients[client_id].send.call_count == 1
    # Assert that an error message was sent

