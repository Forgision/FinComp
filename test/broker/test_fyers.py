from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest
from httpx import HTTPStatusError, Request, Response

from app.web.brokers.fyers.api.auth_api import authenticate_broker
from app.web.brokers.fyers.api.data import (
    BrokerData,
)


# --- Fixtures ---
@pytest.fixture
def mock_settings():
    """Fixture to mock app settings."""
    with patch(
        "app.web.broker.broker.fyers.api.auth_api.settings"
    ) as mock_settings_obj:
        mock_settings_obj.BROKER_API_KEY = "mock_api_key"
        mock_settings_obj.BROKER_API_SECRET = "mock_api_secret"
        yield mock_settings_obj


@pytest.fixture
def mock_httpx_client():
    """Fixture to mock httpx client with async capabilities."""
    with patch(
        "app.web.broker.broker.fyers.api.auth_api.get_httpx_client"
    ) as mock_get_client:
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_sha256():
    """Fixture to mock hashlib.sha256."""
    with patch(
        "app.web.broker.broker.fyers.api.auth_api.hashlib.sha256"
    ) as mock_sha256_obj:
        mock_sha256_obj.return_value.hexdigest.return_value = "mock_app_id_hash"
        yield mock_sha256_obj


@pytest.fixture
def mock_get_br_symbol():
    """Fixture to mock get_br_symbol function."""
    with patch(
        "app.web.broker.broker.fyers.api.data.get_br_symbol"
    ) as mock_get_br_symbol_obj:
        mock_get_br_symbol_obj.return_value = "NSE:SBIN-EQ"
        yield mock_get_br_symbol_obj


@pytest.fixture
def mock_data_get_api_response():
    """Fixture to mock the get_api_response function in data.py."""
    with patch(
        "app.web.broker.broker.fyers.api.data.get_api_response"
    ) as mock_get_api_response_obj:
        yield mock_get_api_response_obj


# --- Test Cases for Authentication ---
class TestFyersAuth:
    @pytest.mark.asyncio
    async def test_authenticate_broker_success(
        self, mock_settings, mock_httpx_client, mock_sha256
    ):
        """Test successful authentication."""
        mock_httpx_client.post.return_value = Response(
            200,
            json={
                "s": "ok",
                "access_token": "mock_access_token",
                "refresh_token": "mock_refresh_token",
                "expires_in": 3600,
            },
        )
        access_token, response_data = await authenticate_broker("mock_request_token")

        assert access_token == "mock_access_token"
        assert response_data["status"] == "success"
        assert response_data["data"]["access_token"] == "mock_access_token"
        mock_sha256.assert_called_once_with(b"mock_api_key:mock_api_secret")
        mock_httpx_client.post.assert_called_once()
        args, kwargs = mock_httpx_client.post.call_args
        assert kwargs["json"]["code"] == "mock_request_token"
        assert kwargs["json"]["appIdHash"] == "mock_app_id_hash"

    @pytest.mark.asyncio
    async def test_authenticate_broker_missing_api_key(
        self, mock_settings, mock_httpx_client
    ):
        """Test authentication failure due to missing API key."""
        mock_settings.BROKER_API_KEY = None
        access_token, response_data = await authenticate_broker("mock_request_token")

        assert access_token is None
        assert response_data["status"] == "error"
        assert "Missing BROKER_API_KEY" in response_data["message"]
        mock_httpx_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_broker_missing_request_token(
        self, mock_settings, mock_httpx_client
    ):
        """Test authentication failure due to missing request token."""
        access_token, response_data = await authenticate_broker(None)

        assert access_token is None
        assert response_data["status"] == "error"
        assert "No request token provided" in response_data["message"]
        mock_httpx_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_broker_api_error(
        self, mock_settings, mock_httpx_client, mock_sha256
    ):
        """Test authentication when Fyers API returns an error."""
        mock_httpx_client.post.return_value = Response(
            200, json={"s": "error", "message": "Invalid auth code"}
        )
        access_token, response_data = await authenticate_broker("mock_request_token")

        assert access_token is None
        assert response_data["status"] == "error"
        assert "API error: Invalid auth code" in response_data["message"]
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_broker_http_error(
        self, mock_settings, mock_httpx_client, mock_sha256
    ):
        """Test authentication when HTTPX raises an HTTP error."""
        mock_httpx_client.post.side_effect = HTTPStatusError(
            "Bad Request",
            request=Request("POST", "http://test.com"),
            response=Response(400),
        )
        access_token, response_data = await authenticate_broker("mock_request_token")

        assert access_token is None
        assert response_data["status"] == "error"
        assert "Authentication failed: Bad Request" in response_data["message"]
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_broker_unexpected_error(
        self, mock_settings, mock_httpx_client, mock_sha256
    ):
        """Test authentication when an unexpected exception occurs."""
        mock_httpx_client.post.side_effect = Exception("Network down")
        access_token, response_data = await authenticate_broker("mock_request_token")

        assert access_token is None
        assert response_data["status"] == "error"
        assert "Authentication failed: Network down" in response_data["message"]
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_broker_no_access_token_in_response(
        self, mock_settings, mock_httpx_client, mock_sha256
    ):
        """Test authentication when API returns 'ok' but no access_token."""
        mock_httpx_client.post.return_value = Response(
            200, json={"s": "ok", "refresh_token": "mock_refresh_token"}
        )
        access_token, response_data = await authenticate_broker("mock_request_token")

        assert access_token is None
        assert response_data["status"] == "error"
        assert (
            "Authentication succeeded but no access token was returned"
            in response_data["message"]
        )
        mock_httpx_client.post.assert_called_once()


@pytest.fixture
def mock_order_get_api_response():
    """Fixture to mock the get_api_response function in order_api.py."""
    with patch(
        "app.web.broker.broker.fyers.api.order_api.get_api_response"
    ) as mock_get_api_response_obj:
        yield mock_get_api_response_obj


@pytest.fixture
def mock_get_br_symbol_order():
    """Fixture to mock get_br_symbol function in order_api.py."""
    with patch(
        "app.web.broker.broker.fyers.api.order_api.get_br_symbol"
    ) as mock_get_br_symbol_obj:
        mock_get_br_symbol_obj.return_value = "NSE:SBIN-EQ"
        yield mock_get_br_symbol_obj


@pytest.fixture
def mock_transform_data():
    """Fixture to mock transform_data function."""
    with patch(
        "app.web.broker.broker.fyers.api.order_api.transform_data"
    ) as mock_transform_data_obj:
        mock_transform_data_obj.return_value = {"transformed": "data"}
        yield mock_transform_data_obj


@pytest.fixture
def mock_transform_modify_order_data():
    """Fixture to mock transform_modify_order_data function."""
    with patch(
        "app.web.broker.broker.fyers.api.order_api.transform_modify_order_data"
    ) as mock_transform_modify_order_data_obj:
        mock_transform_modify_order_data_obj.return_value = {
            "transformed": "modify_data"
        }
        yield mock_transform_modify_order_data_obj


@pytest.fixture
def mock_map_product_type():
    """Fixture to mock map_product_type function."""
    with patch(
        "app.web.broker.broker.fyers.api.order_api.map_product_type"
    ) as mock_map_product_type_obj:
        mock_map_product_type_obj.return_value = "CNC"
        yield mock_map_product_type_obj


# --- Test Cases for BrokerData ---
class TestFyersData:
    @pytest.mark.asyncio
    async def test_get_quotes_success(
        self, mock_get_br_symbol, mock_data_get_api_response
    ):
        """Test successful retrieval of quotes."""
        mock_data_get_api_response.return_value = {
            "s": "ok",
            "d": [
                {
                    "v": {
                        "bid": 100.0,
                        "ask": 101.0,
                        "open_price": 99.0,
                        "high_price": 102.0,
                        "low_price": 98.0,
                        "lp": 100.5,
                        "prev_close_price": 99.5,
                        "volume": 1000,
                    }
                }
            ],
        }
        broker_data = BrokerData("mock_auth_token")
        quotes = broker_data.get_quotes("SBIN", "NSE")

        assert quotes["ltp"] == 100.5
        assert quotes["bid"] == 100.0
        assert quotes["ask"] == 101.0
        mock_get_br_symbol.assert_called_once_with("SBIN", "NSE")
        mock_data_get_api_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_quotes_api_error(
        self, mock_get_br_symbol, mock_data_get_api_response
    ):
        """Test quotes retrieval when Fyers API returns an error."""
        mock_data_get_api_response.return_value = {
            "s": "error",
            "message": "Invalid symbol",
        }
        broker_data = BrokerData("mock_auth_token")

        with pytest.raises(
            Exception,
            match="Error fetching quotes: Error from Fyers API: Invalid symbol",
        ):
            broker_data.get_quotes("INVALID", "NSE")
        mock_get_br_symbol.assert_called_once_with("INVALID", "NSE")
        mock_data_get_api_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_quotes_general_error(
        self, mock_get_br_symbol, mock_data_get_api_response
    ):
        """Test quotes retrieval when an unexpected error occurs."""
        mock_data_get_api_response.side_effect = Exception("Network issue")
        broker_data = BrokerData("mock_auth_token")

        with pytest.raises(Exception, match="Error fetching quotes: Network issue"):
            broker_data.get_quotes("SBIN", "NSE")
        mock_get_br_symbol.assert_called_once_with("SBIN", "NSE")
        mock_data_get_api_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_history_success_daily(
        self, mock_get_br_symbol, mock_data_get_api_response
    ):
        """Test successful retrieval of daily historical data."""
        mock_data_get_api_response.return_value = {
            "s": "ok",
            "candles": [
                [1678886400, 100, 105, 99, 103, 100000]
            ],  # Mock epoch timestamp for 2023-03-15
        }
        broker_data = BrokerData("mock_auth_token")
        df = broker_data.get_history("SBIN", "NSE", "D", "2023-03-15", "2023-03-15")

        assert not df.empty
        assert len(df) == 1
        assert df["close"].iloc[0] == 103
        assert (
            "oi" in df.columns
        )  # Ensure 'oi' column is present even if not in original data
        mock_get_br_symbol.assert_called_once_with("SBIN", "NSE")
        mock_data_get_api_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_history_success_intraday(
        self, mock_get_br_symbol, mock_data_get_api_response
    ):
        """Test successful retrieval of intraday historical data."""
        mock_data_get_api_response.return_value = {
            "s": "ok",
            "candles": [[1678886400, 100, 101, 99, 100.5, 50000]],
        }
        broker_data = BrokerData("mock_auth_token")
        df = broker_data.get_history("SBIN", "NSE", "5m", "2023-03-15", "2023-03-15")

        assert not df.empty
        assert len(df) == 1
        assert df["close"].iloc[0] == 100.5
        assert "oi" in df.columns
        mock_get_br_symbol.assert_called_once_with("SBIN", "NSE")
        mock_data_get_api_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_history_unsupported_timeframe(
        self, mock_get_br_symbol, mock_data_get_api_response
    ):
        """Test historical data retrieval with an unsupported timeframe."""
        broker_data = BrokerData("mock_auth_token")

        with pytest.raises(Exception, match="Unsupported timeframe"):
            broker_data.get_history("SBIN", "NSE", "W", "2023-01-01", "2023-01-31")
        mock_get_br_symbol.assert_called_once_with("SBIN", "NSE")
        mock_data_get_api_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_history_api_error(
        self, mock_get_br_symbol, mock_data_get_api_response
    ):
        """Test historical data retrieval when Fyers API returns an error."""
        mock_data_get_api_response.return_value = {
            "s": "error",
            "message": "No data found",
        }
        broker_data = BrokerData("mock_auth_token")

        df = broker_data.get_history("SBIN", "NSE", "D", "2023-01-01", "2023-01-01")
        assert df.empty
        mock_get_br_symbol.assert_called_once_with("SBIN", "NSE")
        mock_data_get_api_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_history_no_candles(
        self, mock_get_br_symbol, mock_data_get_api_response
    ):
        """Test historical data retrieval when API returns no candles."""
        mock_data_get_api_response.return_value = {"s": "ok", "candles": []}
        broker_data = BrokerData("mock_auth_token")

        df = broker_data.get_history("SBIN", "NSE", "D", "2023-01-01", "2023-01-01")
        assert df.empty
        mock_get_br_symbol.assert_called_once_with("SBIN", "NSE")
        mock_data_get_api_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_history_derivative_with_oi(
        self, mock_get_br_symbol, mock_data_get_api_response
    ):
        """Test historical data retrieval for derivatives with OI."""
        mock_get_br_symbol.return_value = "NFO:NIFTY23MARFUT"  # Mock for derivative
        mock_data_get_api_response.return_value = {
            "s": "ok",
            "candles": [[1678886400, 100, 105, 99, 103, 100000, 50000]],  # With OI
        }
        broker_data = BrokerData("mock_auth_token")
        df = broker_data.get_history("NIFTY", "NFO", "D", "2023-03-15", "2023-03-15")

        assert not df.empty
        assert "oi" in df.columns
        assert df["oi"].iloc[0] == 50000
        mock_get_br_symbol.assert_called_once_with("NIFTY", "NFO")
        mock_data_get_api_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_history_date_in_future(
        self, mock_get_br_symbol, mock_data_get_api_response
    ):
        """Test historical data retrieval when end date is in the future."""
        future_date = (pd.Timestamp.now() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        mock_data_get_api_response.return_value = {
            "s": "ok",
            "candles": [[pd.Timestamp.now().timestamp(), 100, 101, 99, 100.5, 50000]],
        }
        broker_data = BrokerData("mock_auth_token")
        df = broker_data.get_history("SBIN", "NSE", "D", "2023-01-01", future_date)

        assert not df.empty
        mock_get_br_symbol.assert_called_once_with("SBIN", "NSE")
        mock_data_get_api_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_depth_success(
        self, mock_get_br_symbol, mock_data_get_api_response
    ):
        """Test successful retrieval of market depth."""
        mock_data_get_api_response.return_value = {
            "s": "ok",
            "d": {
                "NSE:SBIN-EQ": {
                    "bids": [{"price": 100.0, "volume": 100}],
                    "asks": [{"price": 101.0, "volume": 50}],
                    "totalbuyqty": 1000,
                    "totalsellqty": 500,
                    "h": 102.0,
                    "l": 98.0,
                    "ltp": 100.5,
                    "ltq": 10,
                    "o": 99.0,
                    "c": 99.5,
                    "v": 2000,
                    "oi": 10000,
                }
            },
        }
        broker_data = BrokerData("mock_auth_token")
        depth = broker_data.get_depth("SBIN", "NSE")

        assert depth["ltp"] == 100.5
        assert depth["bids"][0]["price"] == 100.0
        assert depth["asks"][0]["price"] == 101.0
        assert depth["oi"] == 10000
        mock_get_br_symbol.assert_called_once_with("SBIN", "NSE")
        mock_data_get_api_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_depth_api_error(
        self, mock_get_br_symbol, mock_data_get_api_response
    ):
        """Test market depth retrieval when Fyers API returns an error."""
        mock_data_get_api_response.return_value = {
            "s": "error",
            "message": "Invalid symbol",
        }
        broker_data = BrokerData("mock_auth_token")

        with pytest.raises(
            Exception,
            match="Error fetching market depth: Error from Fyers API: Invalid symbol",
        ):
            broker_data.get_depth("INVALID", "NSE")
        mock_get_br_symbol.assert_called_once_with("INVALID", "NSE")
        mock_data_get_api_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_depth_no_data(
        self, mock_get_br_symbol, mock_data_get_api_response
    ):
        """Test market depth retrieval when API returns no data for the symbol."""
        mock_data_get_api_response.return_value = {"s": "ok", "d": {}}
        broker_data = BrokerData("mock_auth_token")

        depth = broker_data.get_depth("SBIN", "NSE")
        assert depth == {}
        mock_get_br_symbol.assert_called_once_with("SBIN", "NSE")
        mock_data_get_api_response.assert_called_once()


# --- Test Cases for Order Management ---
class TestFyersOrder:
    @pytest.mark.asyncio
    async def test_get_order_book_success(self, mock_order_get_api_response):
        """Test successful retrieval of order book."""
        mock_order_get_api_response.return_value = {
            "s": "ok",
            "orderBook": [{"id": "123", "symbol": "NSE:SBIN-EQ", "status": "OPEN"}],
        }
        response = get_order_book("mock_auth_token")
        assert response["s"] == "ok"
        assert len(response["orderBook"]) == 1
        assert response["orderBook"][0]["id"] == "123"
        mock_order_get_api_response.assert_called_once_with(
            "/api/v3/orders", "mock_auth_token"
        )

    @pytest.mark.asyncio
    async def test_get_order_book_api_error(self, mock_order_get_api_response):
        """Test order book retrieval when Fyers API returns an error."""
        mock_order_get_api_response.return_value = {
            "s": "error",
            "message": "Failed to fetch orders",
        }
        response = get_order_book("mock_auth_token")
        assert response["s"] == "error"
        assert "Failed to fetch orders" in response["message"]
        mock_order_get_api_response.assert_called_once_with(
            "/api/v3/orders", "mock_auth_token"
        )

    @pytest.mark.asyncio
    async def test_get_trade_book_success(self, mock_order_get_api_response):
        """Test successful retrieval of trade book."""
        mock_order_get_api_response.return_value = {
            "s": "ok",
            "tradeBook": [{"id": "456", "symbol": "NSE:SBIN-EQ", "qty": 10}],
        }
        response = get_trade_book("mock_auth_token")
        assert response["s"] == "ok"
        assert len(response["tradeBook"]) == 1
        assert response["tradeBook"][0]["id"] == "456"
        mock_order_get_api_response.assert_called_once_with(
            "/api/v3/tradebook", "mock_auth_token"
        )

    @pytest.mark.asyncio
    async def test_get_positions_success(self, mock_order_get_api_response):
        """Test successful retrieval of positions."""
        mock_order_get_api_response.return_value = {
            "s": "ok",
            "netPositions": [{"symbol": "NSE:SBIN-EQ", "netQty": 50}],
        }
        response = get_positions("mock_auth_token")
        assert response["s"] == "ok"
        assert len(response["netPositions"]) == 1
        assert response["netPositions"][0]["netQty"] == 50
        mock_order_get_api_response.assert_called_once_with(
            "/api/v3/positions", "mock_auth_token"
        )

    @pytest.mark.asyncio
    async def test_get_holdings_success(self, mock_order_get_api_response):
        """Test successful retrieval of holdings."""
        mock_order_get_api_response.return_value = {
            "s": "ok",
            "holdings": [{"symbol": "NSE:SBIN-EQ", "qty": 100}],
        }
        response = get_holdings("mock_auth_token")
        assert response["s"] == "ok"
        assert len(response["holdings"]) == 1
        assert response["holdings"][0]["qty"] == 100
        mock_order_get_api_response.assert_called_once_with(
            "/api/v3/holdings", "mock_auth_token"
        )

    @pytest.mark.asyncio
    async def test_get_open_position_found(
        self,
        mock_order_get_api_response,
        mock_get_br_symbol_order,
        mock_map_product_type,
    ):
        """Test retrieval of an open position when found."""
        mock_order_get_api_response.return_value = {
            "s": "ok",
            "netPositions": [
                {"symbol": "NSE:SBIN-EQ", "productType": "CNC", "netQty": 25},
                {"symbol": "NSE:RELIANCE-EQ", "productType": "CNC", "netQty": 30},
            ],
        }
        net_qty = get_open_position("SBIN", "NSE", "CNC", "mock_auth_token")
        assert net_qty == 25
        mock_get_br_symbol_order.assert_called_once_with("SBIN", "NSE")
        mock_order_get_api_response.assert_called_once_with(
            "/api/v3/positions", "mock_auth_token"
        )
        mock_map_product_type.assert_called_once_with("CNC")

    @pytest.mark.asyncio
    async def test_get_open_position_not_found(
        self,
        mock_order_get_api_response,
        mock_get_br_symbol_order,
        mock_map_product_type,
    ):
        """Test retrieval of an open position when not found."""
        mock_order_get_api_response.return_value = {
            "s": "ok",
            "netPositions": [
                {"symbol": "NSE:RELIANCE-EQ", "productType": "CNC", "netQty": 30}
            ],
        }
        net_qty = get_open_position("SBIN", "NSE", "CNC", "mock_auth_token")
        assert net_qty == "0"
        mock_get_br_symbol_order.assert_called_once_with("SBIN", "NSE")
        mock_order_get_api_response.assert_called_once_with(
            "/api/v3/positions", "mock_auth_token"
        )
        mock_map_product_type.assert_called_once_with("CNC")

    @pytest.mark.asyncio
    async def test_place_order_api_success(
        self, mock_settings, mock_httpx_client, mock_transform_data
    ):
        """Test successful order placement."""
        mock_httpx_client.post.return_value = Response(
            200, json={"s": "ok", "id": "ORDER123"}
        )
        mock_httpx_client.post.return_value.status_code = 200  # For compatibility
        data = {"symbol": "SBIN", "exchange": "NSE", "qty": 10, "action": "BUY"}
        response, response_data, order_id = await place_order_api(
            data, "mock_auth_token"
        )

        assert response.status_code == 200
        assert response_data["s"] == "ok"
        assert order_id == "ORDER123"
        mock_transform_data.assert_called_once_with(data)
        mock_httpx_client.post.assert_called_once()
        args, kwargs = mock_httpx_client.post.call_args
        assert kwargs["json"] == {"transformed": "data"}

    @pytest.mark.asyncio
    async def test_place_order_api_failure(
        self, mock_settings, mock_httpx_client, mock_transform_data
    ):
        """Test order placement failure."""
        mock_httpx_client.post.return_value = Response(
            200, json={"s": "error", "message": "Insufficient funds"}
        )
        mock_httpx_client.post.return_value.status_code = 200  # For compatibility
        data = {"symbol": "SBIN", "exchange": "NSE", "qty": 10, "action": "BUY"}
        response, response_data, order_id = await place_order_api(
            data, "mock_auth_token"
        )

        assert response.status_code == 200
        assert response_data["s"] == "error"
        assert order_id is None
        assert "Insufficient funds" in response_data["message"]
        mock_transform_data.assert_called_once_with(data)
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_place_smartorder_api_no_action_needed(
        self,
        mock_order_get_api_response,
        mock_get_br_symbol_order,
        mock_map_product_type,
    ):
        """Test smart order when no action is needed (position matches)."""
        mock_order_get_api_response.return_value = {
            "s": "ok",
            "netPositions": [
                {"symbol": "NSE:SBIN-EQ", "productType": "CNC", "netQty": 10}
            ],
        }
        data = {
            "symbol": "SBIN",
            "exchange": "NSE",
            "product": "CNC",
            "position_size": 10,
            "quantity": 0,
        }
        res, response, orderid = await place_smartorder_api(data, "mock_auth_token")

        assert res is None
        assert response["status"] == "success"
        assert "No action needed" in response["message"]
        assert orderid is None
        mock_get_br_symbol_order.assert_called_once_with("SBIN", "NSE")
        mock_map_product_type.assert_called_once_with("CNC")

    @pytest.mark.asyncio
    async def test_place_smartorder_api_buy_to_increase_position(
        self,
        mock_order_get_api_response,
        mock_get_br_symbol_order,
        mock_map_product_type,
        mock_httpx_client,
        mock_transform_data,
    ):
        """Test smart order to buy and increase an existing position."""
        mock_order_get_api_response.return_value = {
            "s": "ok",
            "netPositions": [
                {"symbol": "NSE:SBIN-EQ", "productType": "CNC", "netQty": 5}
            ],
        }
        mock_httpx_client.post.return_value = Response(
            200, json={"s": "ok", "id": "ORDER123"}
        )
        mock_httpx_client.post.return_value.status_code = 200  # For compatibility
        data = {
            "symbol": "SBIN",
            "exchange": "NSE",
            "product": "CNC",
            "position_size": 10,
            "quantity": 0,
        }
        res, response, orderid = await place_smartorder_api(data, "mock_auth_token")

        assert orderid == "ORDER123"
        assert response["s"] == "ok"
        assert mock_transform_data.call_args[0][0]["action"] == "BUY"
        assert mock_transform_data.call_args[0][0]["quantity"] == "5"

    @pytest.mark.asyncio
    async def test_place_smartorder_api_sell_to_decrease_position(
        self,
        mock_order_get_api_response,
        mock_get_br_symbol_order,
        mock_map_product_type,
        mock_httpx_client,
        mock_transform_data,
    ):
        """Test smart order to sell and decrease an existing position."""
        mock_order_get_api_response.return_value = {
            "s": "ok",
            "netPositions": [
                {"symbol": "NSE:SBIN-EQ", "productType": "CNC", "netQty": 15}
            ],
        }
        mock_httpx_client.post.return_value = Response(
            200, json={"s": "ok", "id": "ORDER456"}
        )
        mock_httpx_client.post.return_value.status_code = 200  # For compatibility
        data = {
            "symbol": "SBIN",
            "exchange": "NSE",
            "product": "CNC",
            "position_size": 10,
            "quantity": 0,
        }
        res, response, orderid = await place_smartorder_api(data, "mock_auth_token")

        assert orderid == "ORDER456"
        assert response["s"] == "ok"
        assert mock_transform_data.call_args[0][0]["action"] == "SELL"
        assert mock_transform_data.call_args[0][0]["quantity"] == "5"

    @pytest.mark.asyncio
    async def test_close_all_positions_success(self, mock_settings, mock_httpx_client):
        """Test successful closing of all positions."""
        mock_httpx_client.request.return_value = Response(
            200, json={"s": "ok", "message": "Positions closed"}
        )
        response_data, status_code = await close_all_positions(
            "mock_api_key", "mock_auth_token"
        )

        assert status_code == 200
        assert response_data["status"] == "success"
        assert "Positions closed" in response_data["message"]
        mock_httpx_client.request.assert_called_once_with(
            "DELETE",
            "https://api-t1.fyers.in/api/v3/positions",
            headers=pytest.ANY,
            json={"exit_all": 1},
        )

    @pytest.mark.asyncio
    async def test_close_all_positions_failure(self, mock_settings, mock_httpx_client):
        """Test failure to close all positions."""
        mock_httpx_client.request.return_value = Response(
            200, json={"s": "error", "message": "Failed to close"}
        )
        response_data, status_code = await close_all_positions(
            "mock_api_key", "mock_auth_token"
        )

        assert status_code == 200
        assert response_data["status"] == "error"
        assert "Failed to close" in response_data["message"]

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, mock_settings, mock_httpx_client):
        """Test successful order cancellation."""
        mock_httpx_client.request.return_value = Response(
            200, json={"s": "ok", "id": "CANCELLED123"}
        )
        response_data, status_code = await cancel_order("ORDER123", "mock_auth_token")

        assert status_code == 200
        assert response_data["status"] == "success"
        assert response_data["orderid"] == "CANCELLED123"
        mock_httpx_client.request.assert_called_once_with(
            "DELETE",
            "https://api-t1.fyers.in/api/v3/orders/sync",
            headers=pytest.ANY,
            json={"id": "ORDER123"},
        )

    @pytest.mark.asyncio
    async def test_cancel_order_failure(self, mock_settings, mock_httpx_client):
        """Test order cancellation failure."""
        mock_httpx_client.request.return_value = Response(
            200, json={"s": "error", "message": "Order not found"}
        )
        response_data, status_code = await cancel_order(
            "NONEXISTENT", "mock_auth_token"
        )

        assert status_code == 200
        assert response_data["status"] == "error"
        assert "Order not found" in response_data["message"]

    @pytest.mark.asyncio
    async def test_modify_order_success(
        self, mock_settings, mock_httpx_client, mock_transform_modify_order_data
    ):
        """Test successful order modification."""
        mock_httpx_client.patch.return_value = Response(
            200, json={"s": "ok", "id": "MODIFIED456"}
        )
        data = {"id": "ORDER456", "qty": 20}
        response_data, status_code = await modify_order(data, "mock_auth_token")

        assert status_code == 200
        assert response_data["status"] == "success"
        assert response_data["orderid"] == "MODIFIED456"
        mock_transform_modify_order_data.assert_called_once_with(data)
        mock_httpx_client.patch.assert_called_once_with(
            "https://api-t1.fyers.in/api/v3/orders/sync",
            headers=pytest.ANY,
            json={"transformed": "modify_data"},
        )

    @pytest.mark.asyncio
    async def test_modify_order_failure(
        self, mock_settings, mock_httpx_client, mock_transform_modify_order_data
    ):
        """Test order modification failure."""
        mock_httpx_client.patch.return_value = Response(
            200, json={"s": "error", "message": "Invalid modification"}
        )
        data = {"id": "ORDER456", "qty": 20}
        response_data, status_code = await modify_order(data, "mock_auth_token")

        assert status_code == 200
        assert response_data["status"] == "error"
        assert "Invalid modification" in response_data["message"]

    @pytest.mark.asyncio
    async def test_cancel_all_orders_api_success(
        self, mock_order_get_api_response, mock_httpx_client
    ):
        """Test successful cancellation of all open orders."""
        mock_order_get_api_response.return_value = {
            "s": "ok",
            "orderBook": [
                {"id": "OPEN1", "status": 4},  # Trigger-pending
                {"id": "OPEN2", "status": 6},  # Open
                {"id": "COMPLETE1", "status": 7},  # Completed
            ],
        }
        mock_httpx_client.request.side_effect = [
            Response(200, json={"s": "ok", "id": "OPEN1"}),
            Response(200, json={"s": "ok", "id": "OPEN2"}),
        ]
        canceled, failed = await cancel_all_orders_api({}, "mock_auth_token")

        assert canceled == ["OPEN1", "OPEN2"]
        assert failed == []
        assert mock_httpx_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_cancel_all_orders_api_no_open_orders(
        self, mock_order_get_api_response, mock_httpx_client
    ):
        """Test cancellation when no open orders are found."""
        mock_order_get_api_response.return_value = {
            "s": "ok",
            "orderBook": [
                {"id": "COMPLETE1", "status": 7},  # Completed
            ],
        }
        canceled, failed = await cancel_all_orders_api({}, "mock_auth_token")

        assert canceled == []
        assert failed == []
        mock_httpx_client.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_all_orders_api_partial_failure(
        self, mock_order_get_api_response, mock_httpx_client
    ):
        """Test partial failure during cancellation of all open orders."""
        mock_order_get_api_response.return_value = {
            "s": "ok",
            "orderBook": [
                {"id": "OPEN1", "status": 4},
                {"id": "OPEN2", "status": 6},
            ],
        }
        mock_httpx_client.request.side_effect = [
            Response(200, json={"s": "ok", "id": "OPEN1"}),
            Response(200, json={"s": "error", "message": "Failed to cancel OPEN2"}),
        ]
        canceled, failed = await cancel_all_orders_api({}, "mock_auth_token")

        assert canceled == ["OPEN1"]
        assert failed == ["OPEN2"]
        assert mock_httpx_client.request.call_count == 2
