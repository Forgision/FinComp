import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.core.services.orderbook_service import get_orderbook


class TestOrderbookService(unittest.TestCase):

    def setUp(self):
        # Setup mocks for import_broker_module
        self.mock_api = AsyncMock()
        self.mock_mapping = unittest.mock.Mock()

        self.mock_broker_funcs = {
            'get_order_book': self.mock_api.get_order_book,
            'map_order_data': self.mock_mapping.map_order_data,
            'calculate_order_statistics': self.mock_mapping.calculate_order_statistics,
            'transform_order_data': self.mock_mapping.transform_order_data
        }
        self.patcher = patch('app.core.services.orderbook_service.import_broker_module', return_value=self.mock_broker_funcs)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    async def _test_get_orderbook_success_with_auth_token(self):
        """Test get_orderbook with a valid auth_token."""
        auth_token = "some_auth_token"
        broker = "test_broker"

        # Configure mock responses
        self.mock_broker_funcs['get_order_book'].return_value = {"status": "success", "data": [{"symbol": "TEST"}]}
        self.mock_broker_funcs['map_order_data'].return_value = [{"symbol": "TEST", "mapped": True}]
        self.mock_broker_funcs['transform_order_data'].return_value = [{"symbol": "TEST", "transformed": True}]
        self.mock_broker_funcs['calculate_order_statistics'].return_value = {"total": 1}

        success, response, status_code = await get_orderbook(auth_token=auth_token, broker=broker)

        self.assertTrue(success)
        self.assertEqual(status_code, 200)
        self.assertIn("orders", response["data"])
        self.assertIn("statistics", response["data"])
        self.assertEqual(response["data"]["orders"], [{"symbol": "TEST", "transformed": True}])
        self.assertEqual(response["data"]["statistics"], {"total": 1})
        self.mock_broker_funcs['get_order_book'].assert_called_once_with(auth_token)
        self.mock_broker_funcs['map_order_data'].assert_called_once()
        self.mock_broker_funcs['transform_order_data'].assert_called_once()
        self.mock_broker_funcs['calculate_order_statistics'].assert_called_once()

    def test_get_orderbook_success_with_auth_token_sync(self):
        asyncio.run(self._test_get_orderbook_success_with_auth_token())

    async def _test_get_orderbook_success_with_api_key(self):
        """Test get_orderbook with a valid API key (analyze mode)."""
        api_key = "some_api_key"

        with patch('app.core.services.orderbook_service.get_analyze_mode', return_value=True) as mock_get_analyze_mode, \
             patch('app.core.services.orderbook_service.sandbox_get_orderbook', new_callable=AsyncMock) as mock_sandbox_get_orderbook:

            mock_sandbox_get_orderbook.return_value = (True, {
                'status': 'success',
                'data': {
                    'orders': [{"symbol": "SANDBOX", "quantity": 10}],
                    'statistics': {"total_orders": 1}
                }
            }, 200)

            success, response, status_code = await get_orderbook(api_key=api_key)

            mock_get_analyze_mode.assert_called_once()
            mock_sandbox_get_orderbook.assert_called_once_with(api_key, {'apikey': api_key})

        self.assertTrue(success)
        self.assertEqual(status_code, 200)
        self.assertIn("orders", response["data"])
        self.assertIn("statistics", response["data"])
        self.assertEqual(response["data"]["orders"], [{"symbol": "SANDBOX", "quantity": 10}])
        self.assertEqual(response["data"]["statistics"], {"total_orders": 1})

    def test_get_orderbook_success_with_api_key_sync(self):
        asyncio.run(self._test_get_orderbook_success_with_api_key())

    async def _test_get_orderbook_no_auth_or_api_key(self):
        """Test get_orderbook without auth_token or api_key."""
        success, response, status_code = await get_orderbook()

        self.assertFalse(success)
        self.assertEqual(status_code, 400)
        self.assertIn("message", response)
        self.assertEqual(response["message"], "Either api_key or both auth_token and broker must be provided")

    def test_get_orderbook_no_auth_or_api_key_sync(self):
        asyncio.run(self._test_get_orderbook_no_auth_or_api_key())

    async def _test_get_orderbook_broker_module_not_found(self):
        """Test get_orderbook when broker module cannot be imported."""
        with patch('app.core.services.orderbook_service.import_broker_module', return_value=None):
            success, response, status_code = await get_orderbook(auth_token="token", broker="non_existent_broker")

            self.assertFalse(success)
            self.assertEqual(status_code, 404)
            self.assertIn("message", response)
            self.assertEqual(response["message"], "Broker-specific module not found")

    def test_get_orderbook_broker_module_not_found_sync(self):
        asyncio.run(self._test_get_orderbook_broker_module_not_found())

if __name__ == '__main__':
    unittest.main()
