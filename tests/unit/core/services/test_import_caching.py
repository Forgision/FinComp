
import unittest
from unittest.mock import MagicMock, patch
import sys
from app.core.services import holdings_service, orderbook_service, positionbook_service, tradebook_service

class TestImportCaching(unittest.TestCase):
    def test_import_caching_holdings(self):
        self._test_caching(holdings_service)

    def test_import_caching_orderbook(self):
        self._test_caching(orderbook_service)

    def test_import_caching_positionbook(self):
        self._test_caching(positionbook_service)

    def test_import_caching_tradebook(self):
        self._test_caching(tradebook_service)

    def _test_caching(self, service_module):
        # Clear cache first
        service_module.import_broker_module.cache_clear()

        with patch('importlib.import_module') as mock_import:
            # Mock the return value of import_module
            mock_module = MagicMock()
            mock_import.return_value = mock_module

            # First call
            service_module.import_broker_module("test_broker")

            # Second call
            service_module.import_broker_module("test_broker")

            # Check that import_module was called only once (because of caching)
            # Actually, import_module is called twice per broker (api and mapping),
            # so we expect 2 calls for the first invocation, and 0 additional calls for the second.
            self.assertEqual(mock_import.call_count, 2)

            # Clear cache and call again
            service_module.import_broker_module.cache_clear()
            service_module.import_broker_module("test_broker")
            self.assertEqual(mock_import.call_count, 4)

if __name__ == '__main__':
    unittest.main()
