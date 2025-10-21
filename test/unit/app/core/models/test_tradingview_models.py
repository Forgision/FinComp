import unittest
from pydantic import ValidationError
from app.core.models.tradingview_models import TradingViewRequest

class TestTradingViewRequest(unittest.TestCase):
    def test_trading_view_request_valid(self):
        """Test valid TradingViewRequest data."""
        data = {
            "symbol": "AAPL",
            "exchange": "NASDAQ",
            "product": "equity"
        }
        request = TradingViewRequest(**data)
        self.assertEqual(request.symbol, "AAPL")
        self.assertEqual(request.exchange, "NASDAQ")
        self.assertEqual(request.product, "equity")

    def test_trading_view_request_invalid_symbol_min_length(self):
        """Test TradingViewRequest with symbol too short."""
        data = {
            "symbol": "",
            "exchange": "NASDAQ",
            "product": "equity"
        }
        with self.assertRaises(ValidationError):
            TradingViewRequest(**data)

    def test_trading_view_request_invalid_symbol_max_length(self):
        """Test TradingViewRequest with symbol too long."""
        data = {
            "symbol": "A" * 51,
            "exchange": "NASDAQ",
            "product": "equity"
        }
        with self.assertRaises(ValidationError):
            TradingViewRequest(**data)

    def test_trading_view_request_invalid_exchange_min_length(self):
        """Test TradingViewRequest with exchange too short."""
        data = {
            "symbol": "AAPL",
            "exchange": "",
            "product": "equity"
        }
        with self.assertRaises(ValidationError):
            TradingViewRequest(**data)

    def test_trading_view_request_invalid_exchange_max_length(self):
        """Test TradingViewRequest with exchange too long."""
        data = {
            "symbol": "AAPL",
            "exchange": "E" * 51,
            "product": "equity"
        }
        with self.assertRaises(ValidationError):
            TradingViewRequest(**data)

    def test_trading_view_request_invalid_product_min_length(self):
        """Test TradingViewRequest with product too short."""
        data = {
            "symbol": "AAPL",
            "exchange": "NASDAQ",
            "product": ""
        }
        with self.assertRaises(ValidationError):
            TradingViewRequest(**data)

    def test_trading_view_request_invalid_product_max_length(self):
        """Test TradingViewRequest with product too long."""
        data = {
            "symbol": "AAPL",
            "exchange": "NASDAQ",
            "product": "P" * 51
        }
        with self.assertRaises(ValidationError):
            TradingViewRequest(**data)

    def test_trading_view_request_missing_field(self):
        """Test TradingViewRequest with a missing field."""
        data = {
            "exchange": "NASDAQ",
            "product": "equity"
        }
        with self.assertRaises(ValidationError):
            TradingViewRequest(**data)

if __name__ == '__main__':
    unittest.main()
