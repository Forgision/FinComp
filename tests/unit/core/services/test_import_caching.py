import unittest
from unittest.mock import patch, MagicMock
import sys

# Mock dependencies to allow importing the service
sys.modules["app.core.schemas.auth_db"] = MagicMock()
sys.modules["app.utils.logging"] = MagicMock()
sys.modules["app.core.schemas.settings_db"] = MagicMock()
sys.modules["services.sandbox_service"] = MagicMock()

# Import the services
from app.core.services.holdings_service import import_broker_module as holdings_import
from app.core.services.orderbook_service import import_broker_module as orderbook_import
from app.core.services.positionbook_service import import_broker_module as positionbook_import
from app.core.services.tradebook_service import import_broker_module as tradebook_import

class TestImportCaching(unittest.TestCase):
    def setUp(self):
        # clear cache before each test
        holdings_import.cache_clear()
        orderbook_import.cache_clear()
        positionbook_import.cache_clear()
        tradebook_import.cache_clear()

    @patch("importlib.import_module")
    def test_holdings_caching(self, mock_import):
        # Setup mock return
        mock_module = MagicMock()
        mock_import.return_value = mock_module

        # Call twice
        holdings_import("broker1")
        holdings_import("broker1")

        # Assert import called only twice (once for api, once for mapping) per broker,
        # but since we cache the result, the second call to holdings_import shouldn't trigger imports.
        # So for one call, we expect 2 calls to import_module.
        # For two calls, we still expect 2 calls total.

        self.assertEqual(mock_import.call_count, 2)

    @patch("importlib.import_module")
    def test_orderbook_caching(self, mock_import):
        mock_module = MagicMock()
        mock_import.return_value = mock_module

        orderbook_import("broker2")
        orderbook_import("broker2")

        self.assertEqual(mock_import.call_count, 2)

    @patch("importlib.import_module")
    def test_positionbook_caching(self, mock_import):
        mock_module = MagicMock()
        mock_import.return_value = mock_module

        positionbook_import("broker3")
        positionbook_import("broker3")

        self.assertEqual(mock_import.call_count, 2)

    @patch("importlib.import_module")
    def test_tradebook_caching(self, mock_import):
        mock_module = MagicMock()
        mock_import.return_value = mock_module

        tradebook_import("broker4")
        tradebook_import("broker4")

        self.assertEqual(mock_import.call_count, 2)

if __name__ == "__main__":
    unittest.main()
