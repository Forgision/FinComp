import pytest
from pydantic import ValidationError
from app.core.models.tradingview_models import TradingViewRequest

def test_trading_view_request_valid():
    """Test valid TradingViewRequest data."""
    data = {
        "symbol": "AAPL",
        "exchange": "NASDAQ",
        "product": "equity"
    }
    request = TradingViewRequest(**data)
    assert request.symbol == "AAPL"
    assert request.exchange == "NASDAQ"
    assert request.product == "equity"

def test_trading_view_request_invalid_symbol_min_length():
    """Test TradingViewRequest with symbol too short."""
    data = {
        "symbol": "",
        "exchange": "NASDAQ",
        "product": "equity"
    }
    with pytest.raises(ValidationError):
        TradingViewRequest(**data)

def test_trading_view_request_invalid_symbol_max_length():
    """Test TradingViewRequest with symbol too long."""
    data = {
        "symbol": "A" * 51,
        "exchange": "NASDAQ",
        "product": "equity"
    }
    with pytest.raises(ValidationError):
        TradingViewRequest(**data)

def test_trading_view_request_invalid_exchange_min_length():
    """Test TradingViewRequest with exchange too short."""
    data = {
        "symbol": "AAPL",
        "exchange": "",
        "product": "equity"
    }
    with pytest.raises(ValidationError):
        TradingViewRequest(**data)

def test_trading_view_request_invalid_exchange_max_length():
    """Test TradingViewRequest with exchange too long."""
    data = {
        "symbol": "AAPL",
        "exchange": "E" * 51,
        "product": "equity"
    }
    with pytest.raises(ValidationError):
        TradingViewRequest(**data)

def test_trading_view_request_invalid_product_min_length():
    """Test TradingViewRequest with product too short."""
    data = {
        "symbol": "AAPL",
        "exchange": "NASDAQ",
        "product": ""
    }
    with pytest.raises(ValidationError):
        TradingViewRequest(**data)

def test_trading_view_request_invalid_product_max_length():
    """Test TradingViewRequest with product too long."""
    data = {
        "symbol": "AAPL",
        "exchange": "NASDAQ",
        "product": "P" * 51
    }
    with pytest.raises(ValidationError):
        TradingViewRequest(**data)

def test_trading_view_request_missing_field():
    """Test TradingViewRequest with a missing field."""
    data = {
        "exchange": "NASDAQ",
        "product": "equity"
    }
    with pytest.raises(ValidationError):
        TradingViewRequest(**data)
