import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from app.websocket.server import WebSocketProxy

class TestWebSocketProxy(unittest.TestCase):

    @patch('app.websocket.server.websockets.serve')
    @patch('app.websocket.server.zmq.asyncio.Context')
    def setUp(self, mock_zmq_context, mock_websockets_serve):
        self.proxy = WebSocketProxy()

    @patch('app.websocket.server.verify_api_key', return_value="test_user")
    @patch('app.websocket.server.get_broker_name', return_value="finvasia")
    @patch('app.websocket.server.create_broker_adapter')
    def test_authenticate_client_success(self, mock_create_broker_adapter, mock_get_broker_name, mock_verify_api_key):
        mock_adapter = MagicMock()
        mock_adapter.initialize.return_value = {"success": True}
        mock_adapter.connect.return_value = {"success": True}
        mock_create_broker_adapter.return_value = mock_adapter
        
        client_id = 12345
        self.proxy.clients[client_id] = AsyncMock()
        
        async def run_test():
            await self.proxy.authenticate_client(client_id, {"api_key": "test_api_key"})
            self.proxy.clients[client_id].send.assert_called_once()
            # Further assertions can be made on the content of the sent message

        asyncio.run(run_test())

    def test_process_client_message_invalid_json(self):
        client_id = 12345
        self.proxy.clients[client_id] = AsyncMock()
        
        async def run_test():
            await self.proxy.process_client_message(client_id, "invalid json")
            self.proxy.clients[client_id].send.assert_called_once()
            # Assert that an error message was sent

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()