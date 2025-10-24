import json
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
import pytz
from app.core.config import settings
from app.broker.broker.fivepaisa.api.auth_api import authenticate_broker
from app.broker.broker.fivepaisa.api.data import BrokerData, get_api_response, map_interval
from app.broker.broker.fivepaisa.api.order_api import (
    cancel_all_orders_api,
    cancel_order,
    close_all_positions,
    get_holdings,
    get_open_position,
    get_order_book,
    get_positions,
    get_trade_book,
    modify_order,
    place_order_api,
    place_smartorder_api,
)


@pytest.fixture
def mock_settings():
    """Fixture to mock settings."""
    with patch("app.core.config.settings", autospec=True) as mock_settings:
        mock_settings.BROKER_API_KEY = "mock_api_key:::mock_user_id:::mock_client_id"
        mock_settings.BROKER_API_SECRET = "mock_api_secret"
        mock_settings.FIVEPAISA_BASE_URL = "https://mock.fivepaisa.com"
        yield mock_settings


@pytest.fixture
def mock_httpx_client():
    """Fixture to mock httpx.AsyncClient."""
    with patch("app.utils.httpx_client.get_httpx_client", autospec=True) as mock_get_client:
        mock_client = MagicMock(spec=httpx.Client)
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_get_token():
    """Fixture to mock app.db.token_db.get_token."""
    with patch("app.db.token_db.get_token", autospec=True) as mock_get_token:
        mock_get_token.return_value = "12345"
        yield mock_get_token


@pytest.fixture
def mock_get_br_symbol():
    """Fixture to mock app.db.token_db.get_br_symbol."""
    with patch("app.db.token_db.get_br_symbol", autospec=True) as mock_get_br_symbol:
        mock_get_br_symbol.return_value = "MOCK_SYMBOL"
        yield mock_get_br_symbol


@pytest.fixture
def mock_get_symbol():
    """Fixture to mock app.db.token_db.get_symbol."""
    with patch("app.db.token_db.get_symbol", autospec=True) as mock_get_symbol:
        mock_get_symbol.return_value = "MOCK_SYMBOL_OPENALGO"
        yield mock_get_symbol


@pytest.fixture
def mock_map_exchange():
    """Fixture to mock app.web.broker.fivepaisa.mapping.transform_data.map_exchange."""
    with patch(
        "app.web.broker.fivepaisa.mapping.transform_data.map_exchange", autospec=True
    ) as mock_map_exchange:
        mock_map_exchange.return_value = "MOCK_EXCH"
        yield mock_map_exchange


@pytest.fixture
def mock_map_exchange_type():
    """Fixture to mock app.web.broker.fivepaisa.mapping.transform_data.map_exchange_type."""
    with patch(
        "app.web.broker.fivepaisa.mapping.transform_data.map_exchange_type",
        autospec=True,
    ) as mock_map_exchange_type:
        mock_map_exchange_type.return_value = "MOCK_EXCH_TYPE"
        yield mock_map_exchange_type


@pytest.fixture
def mock_reverse_map_exchange():
    """Fixture to mock app.web.broker.fivepaisa.mapping.transform_data.reverse_map_exchange."""
    with patch(
        "app.web.broker.fivepaisa.mapping.transform_data.reverse_map_exchange",
        autospec=True,
    ) as mock_reverse_map_exchange:
        mock_reverse_map_exchange.return_value = "MOCK_OPENALGO_EXCHANGE"
        yield mock_reverse_map_exchange


@pytest.fixture
def mock_reverse_map_product_type():
    """Fixture to mock app.web.broker.fivepaisa.mapping.transform_data.reverse_map_product_type."""
    with patch(
        "app.web.broker.fivepaisa.mapping.transform_data.reverse_map_product_type",
        autospec=True,
    ) as mock_reverse_map_product_type:
        mock_reverse_map_product_type.return_value = "MOCK_OPENALGO_PRODUCT"
        yield mock_reverse_map_product_type


@pytest.fixture
def mock_transform_data():
    """Fixture to mock app.web.broker.fivepaisa.mapping.transform_data.transform_data."""
    with patch(
        "app.web.broker.fivepaisa.mapping.transform_data.transform_data", autospec=True
    ) as mock_transform_data:
        mock_transform_data.return_value = {"mock": "transformed_data"}
        yield mock_transform_data


@pytest.fixture
def mock_transform_modify_order_data():
    """Fixture to mock app.web.broker.fivepaisa.mapping.transform_data.transform_modify_order_data."""
    with patch(
        "app.web.broker.broker.fivepaisa.api.order_api.transform_modify_order_data",
        autospec=True,
    ) as mock_transform_modify_order_data:
        mock_transform_modify_order_data.return_value = {"mock": "transformed_modify_data"}
        yield mock_transform_modify_order_data


# --- Tests for auth_api.py ---


@pytest.mark.asyncio
async def test_authenticate_broker_success(mock_settings, mock_httpx_client):
    """Test successful authentication."""
    mock_response_totp = MagicMock()
    mock_response_totp.status_code = 200
    mock_response_totp.json.return_value = {
        "body": {"RequestToken": "mock_request_token"}
    }

    mock_response_token = MagicMock()
    mock_response_token.status_code = 200
    mock_response_token.json.return_value = {
        "body": {"AccessToken": "mock_access_token"}
    }

    mock_httpx_client.post.side_effect = [mock_response_totp, mock_response_token]

    token, error = await authenticate_broker("client@example.com", "1234", "654321")

    assert token == "mock_access_token"
    assert error is None
    assert mock_httpx_client.post.call_count == 2


@pytest.mark.asyncio
async def test_authenticate_broker_missing_config(mock_settings, mock_httpx_client):
    """Test authentication with missing BROKER_API_KEY or BROKER_API_SECRET."""
    mock_settings.BROKER_API_KEY = None
    token, error = await authenticate_broker("client@example.com", "1234", "654321")

    assert token is None
    assert "BROKER_API_KEY or BROKER_API_SECRET not found" in error
    mock_httpx_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_authenticate_broker_incorrect_api_key_format(mock_settings, mock_httpx_client):
    """Test authentication with incorrect BROKER_API_KEY format."""
    mock_settings.BROKER_API_KEY = "incorrect_format"
    token, error = await authenticate_broker("client@example.com", "1234", "654321")

    assert token is None
    assert "BROKER_API_KEY format is incorrect" in error
    mock_httpx_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_authenticate_broker_totp_login_failure(mock_settings, mock_httpx_client):
    """Test TOTP login failure."""
    mock_response_totp = MagicMock()
    mock_response_totp.status_code = 200
    mock_response_totp.json.return_value = {
        "body": {"Message": "Invalid TOTP"}
    }  # Missing RequestToken

    mock_httpx_client.post.return_value = mock_response_totp

    token, error = await authenticate_broker("client@example.com", "1234", "654321")

    assert token is None
    assert "TOTP Login Error: Invalid TOTP" in error
    mock_httpx_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_authenticate_broker_access_token_failure(mock_settings, mock_httpx_client):
    """Test access token retrieval failure."""
    mock_response_totp = MagicMock()
    mock_response_totp.status_code = 200
    mock_response_totp.json.return_value = {
        "body": {"RequestToken": "mock_request_token"}
    }

    mock_response_token = MagicMock()
    mock_response_token.status_code = 200
    mock_response_token.json.return_value = {
        "body": {"Message": "Invalid Request Token"}
    }  # Missing AccessToken

    mock_httpx_client.post.side_effect = [mock_response_totp, mock_response_token]

    token, error = await authenticate_broker("client@example.com", "1234", "654321")

    assert token is None
    assert "Access Token Error: Invalid Request Token" in error
    assert mock_httpx_client.post.call_count == 2


@pytest.mark.asyncio
async def test_authenticate_broker_http_status_error(mock_settings, mock_httpx_client):
    """Test HTTPStatusError during authentication."""
    mock_httpx_client.post.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=httpx.Request("POST", "url"), response=httpx.Response(400)
    )

    token, error = await authenticate_broker("client@example.com", "1234", "654321")

    assert token is None
    assert "HTTP error occurred: 400" in error


@pytest.mark.asyncio
async def test_authenticate_broker_request_error(mock_settings, mock_httpx_client):
    """Test httpx.RequestError during authentication."""
    mock_httpx_client.post.side_effect = httpx.RequestError(
        "Network error", request=httpx.Request("POST", "url")
    )

    token, error = await authenticate_broker("client@example.com", "1234", "654321")

    assert token is None
    assert "Request error occurred: Network error" in error


@pytest.mark.asyncio
async def test_authenticate_broker_json_decode_error(mock_settings, mock_httpx_client):
    """Test JSONDecodeError during authentication."""
    mock_response_totp = MagicMock()
    mock_response_totp.status_code = 200
    mock_response_totp.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)

    mock_httpx_client.post.return_value = mock_response_totp

    token, error = await authenticate_broker("client@example.com", "1234", "654321")

    assert token is None
    assert "Failed to parse JSON response" in error


@pytest.mark.asyncio
async def test_authenticate_broker_generic_exception(mock_settings, mock_httpx_client):
    """Test generic exception during authentication."""
    mock_httpx_client.post.side_effect = Exception("Something went wrong")

    token, error = await authenticate_broker("client@example.com", "1234", "654321")

    assert token is None
    assert "Something went wrong" in error


# --- Tests for data.py functions and BrokerData methods ---


@pytest.mark.asyncio
async def test_get_api_response_get_success(mock_httpx_client, mock_settings):
    """Test successful GET API response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success", "data": "test_data"}
    mock_httpx_client.get.return_value = mock_response

    endpoint = "/test/endpoint"
    auth_token = "mock_auth_token"
    response_data = await get_api_response(endpoint, auth_token, method="GET")

    assert response_data == {"status": "success", "data": "test_data"}
    mock_httpx_client.get.assert_called_once_with(
        f"{mock_settings.FIVEPAISA_BASE_URL}{endpoint}",
        headers={"Authorization": f"bearer {auth_token}", "Content-Type": "application/json"},
    )


@pytest.mark.asyncio
async def test_get_api_response_post_success(mock_httpx_client, mock_settings):
    """Test successful POST API response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success", "data": "test_data"}
    mock_httpx_client.post.return_value = mock_response

    endpoint = "/test/endpoint"
    auth_token = "mock_auth_token"
    payload = json.dumps({"key": "value"})
    response_data = await get_api_response(endpoint, auth_token, method="POST", payload=payload)

    assert response_data == {"status": "success", "data": "test_data"}
    mock_httpx_client.post.assert_called_once_with(
        f"{mock_settings.FIVEPAISA_BASE_URL}{endpoint}",
        content=payload,
        headers={"Authorization": f"bearer {auth_token}", "Content-Type": "application/json"},
    )


@pytest.mark.asyncio
async def test_get_api_response_http_status_error(mock_httpx_client, mock_settings):
    """Test HTTPStatusError during API call."""
    mock_httpx_client.get.side_effect = httpx.HTTPStatusError(
        "Bad Request",
        request=httpx.Request("GET", "url"),
        response=httpx.Response(400, request=httpx.Request("GET", "url"), content=b"Error"),
    )

    endpoint = "/test/endpoint"
    auth_token = "mock_auth_token"

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await get_api_response(endpoint, auth_token)

    assert exc_info.type == httpx.HTTPStatusError
    assert "HTTP error occurred: 400" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_api_response_request_error(mock_httpx_client, mock_settings):
    """Test httpx.RequestError during API call."""
    mock_httpx_client.get.side_effect = httpx.RequestError(
        "Network error", request=httpx.Request("GET", "url")
    )

    endpoint = "/test/endpoint"
    auth_token = "mock_auth_token"

    with pytest.raises(httpx.RequestError) as exc_info:
        await get_api_response(endpoint, auth_token)

    assert exc_info.type == httpx.RequestError
    assert "Request error occurred: Network error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_api_response_generic_exception(mock_httpx_client, mock_settings):
    """Test generic exception during API call."""
    mock_httpx_client.get.side_effect = Exception("Unknown error")

    endpoint = "/test/endpoint"
    auth_token = "mock_auth_token"

    with pytest.raises(Exception) as exc_info:
        await get_api_response(endpoint, auth_token)

    assert exc_info.type == Exception
    assert "An error occurred: Unknown error" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.data.get_token", return_value="12345")
@patch("app.web.broker.broker.fivepaisa.api.data.get_br_symbol", return_value="MOCK_BR_SYMBOL")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange", return_value="NSE")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange_type", return_value="C")
async def test_get_quotes_success(
    mock_map_exchange_type,
    mock_map_exchange,
    mock_get_br_symbol,
    mock_get_token,
    mock_httpx_client,
    mock_settings,
):
    """Test successful retrieval of quotes."""
    mock_snapshot_response = MagicMock()
    mock_snapshot_response.status_code = 200
    mock_snapshot_response.json.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {
            "Data": [
                {
                    "LastTradedPrice": 100.50,
                    "High": 101.00,
                    "Low": 99.00,
                    "Open": 100.00,
                    "PClose": 99.50,
                    "Volume": 1000,
                }
            ]
        },
    }

    # Mock get_market_depth to return processed data
    with patch(
        "app.web.broker.broker.fivepaisa.api.data.BrokerData.get_market_depth",
        return_value={"bid": 99.75, "ask": 100.75},
    ) as mock_get_market_depth:
        mock_httpx_client.post.return_value = mock_snapshot_response

        broker_data = BrokerData("mock_auth_token")
        quotes = await broker_data.get_quotes("TESTSYMBOL", "NSE")

        assert quotes == {
            "ask": 100.75,
            "bid": 99.75,
            "high": 101.00,
            "low": 99.00,
            "ltp": 100.50,
            "open": 100.00,
            "prev_close": 99.50,
            "volume": 1000,
        }
        mock_httpx_client.post.assert_called_once()
        mock_get_market_depth.assert_called_once_with("TESTSYMBOL", "NSE")


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.data.get_token", return_value="12345")
@patch("app.web.broker.broker.fivepaisa.api.data.get_br_symbol", return_value="MOCK_BR_SYMBOL")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange", return_value="NSE")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange_type", return_value="C")
async def test_get_quotes_snapshot_failure(
    mock_map_exchange_type,
    mock_map_exchange,
    mock_get_br_symbol,
    mock_get_token,
    mock_httpx_client,
    mock_settings,
):
    """Test get_quotes when market snapshot API returns failure."""
    mock_snapshot_response = MagicMock()
    mock_snapshot_response.status_code = 200
    mock_snapshot_response.json.return_value = {
        "head": {"statusDescription": "Failure"},
        "body": {"Data": []},
    }
    mock_httpx_client.post.return_value = mock_snapshot_response

    broker_data = BrokerData("mock_auth_token")
    quotes = await broker_data.get_quotes("TESTSYMBOL", "NSE")

    assert quotes is None
    mock_httpx_client.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.data.get_token", return_value="12345")
@patch("app.web.broker.broker.fivepaisa.api.data.get_br_symbol", return_value="MOCK_BR_SYMBOL")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange", return_value="NSE")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange_type", return_value="C")
async def test_get_quotes_market_depth_none(
    mock_map_exchange_type,
    mock_map_exchange,
    mock_get_br_symbol,
    mock_get_token,
    mock_httpx_client,
    mock_settings,
):
    """Test get_quotes when get_market_depth returns None."""
    mock_snapshot_response = MagicMock()
    mock_snapshot_response.status_code = 200
    mock_snapshot_response.json.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {
            "Data": [
                {
                    "LastTradedPrice": 100.50,
                    "High": 101.00,
                    "Low": 99.00,
                    "Open": 100.00,
                    "PClose": 99.50,
                    "Volume": 1000,
                }
            ]
        },
    }

    with patch(
        "app.web.broker.broker.fivepaisa.api.data.BrokerData.get_market_depth",
        return_value=None,
    ) as mock_get_market_depth:
        mock_httpx_client.post.return_value = mock_snapshot_response

        broker_data = BrokerData("mock_auth_token")
        quotes = await broker_data.get_quotes("TESTSYMBOL", "NSE")

        assert quotes == {
            "ask": 0,
            "bid": 0,
            "high": 101.00,
            "low": 99.00,
            "ltp": 100.50,
            "open": 100.00,
            "prev_close": 99.50,
            "volume": 1000,
        }
        mock_httpx_client.post.assert_called_once()
        mock_get_market_depth.assert_called_once_with("TESTSYMBOL", "NSE")


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.data.get_token", return_value="12345")
@patch("app.web.broker.broker.fivepaisa.api.data.get_br_symbol", return_value="MOCK_BR_SYMBOL")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange", return_value="NSE")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange_type", return_value="C")
async def test_get_quotes_prev_close_fallback(
    mock_map_exchange_type,
    mock_map_exchange,
    mock_get_br_symbol,
    mock_get_token,
    mock_httpx_client,
    mock_settings,
):
    """Test get_quotes with fallback for prev_close."""
    mock_snapshot_response = MagicMock()
    mock_snapshot_response.status_code = 200
    mock_snapshot_response.json.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {
            "Data": [
                {
                    "LastTradedPrice": 100.50,
                    "High": 101.00,
                    "Low": 99.00,
                    "Open": 100.00,
                    "PreviousClose": 99.50,  # PClose missing, use PreviousClose
                    "Volume": 1000,
                }
            ]
        },
    }

    with patch(
        "app.web.broker.broker.fivepaisa.api.data.BrokerData.get_market_depth",
        return_value={"bid": 99.75, "ask": 100.75},
    ) as mock_get_market_depth:
        mock_httpx_client.post.return_value = mock_snapshot_response

        broker_data = BrokerData("mock_auth_token")
        quotes = await broker_data.get_quotes("TESTSYMBOL", "NSE")

        assert quotes["prev_close"] == 99.50
        mock_httpx_client.post.assert_called_once()
        mock_get_market_depth.assert_called_once_with("TESTSYMBOL", "NSE")


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.data.get_token", return_value="12345")
@patch("app.web.broker.broker.fivepaisa.api.data.get_br_symbol", return_value="MOCK_BR_SYMBOL")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange", return_value="NSE")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange_type", return_value="C")
async def test_get_quotes_exception_handling(
    mock_map_exchange_type,
    mock_map_exchange,
    mock_get_br_symbol,
    mock_get_token,
    mock_httpx_client,
    mock_settings,
):
    """Test get_quotes exception handling."""
    mock_httpx_client.post.side_effect = Exception("Network error")

    broker_data = BrokerData("mock_auth_token")
    quotes = await broker_data.get_quotes("TESTSYMBOL", "NSE")

    assert quotes is None
    mock_httpx_client.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.data.get_token", return_value="12345")
@patch("app.web.broker.broker.fivepaisa.api.data.get_br_symbol", return_value="MOCK_BR_SYMBOL")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange", return_value="NSE")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange_type", return_value="C")
async def test_get_market_depth_success(
    mock_map_exchange_type,
    mock_map_exchange,
    mock_get_br_symbol,
    mock_get_token,
    mock_httpx_client,
    mock_settings,
):
    """Test successful retrieval of market depth."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {
            "MarketDepthData": [
                {"Price": "100.00", "Quantity": "100", "BbBuySellFlag": 66},  # Bid
                {"Price": "101.00", "Quantity": "200", "BbBuySellFlag": 83},  # Ask
            ]
        },
    }
    mock_httpx_client.post.return_value = mock_response

    broker_data = BrokerData("mock_auth_token")
    depth = await broker_data.get_market_depth("TESTSYMBOL", "NSE")

    assert depth == {"bid": 100.00, "ask": 101.00}
    mock_httpx_client.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.data.get_token", return_value="12345")
@patch("app.web.broker.broker.fivepaisa.api.data.get_br_symbol", return_value="MOCK_BR_SYMBOL")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange", return_value="NSE")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange_type", return_value="C")
async def test_get_market_depth_api_failure(
    mock_map_exchange_type,
    mock_map_exchange,
    mock_get_br_symbol,
    mock_get_token,
    mock_httpx_client,
    mock_settings,
):
    """Test get_market_depth when API returns failure status."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Failure"},
        "body": {"MarketDepthData": []},
    }
    mock_httpx_client.post.return_value = mock_response

    broker_data = BrokerData("mock_auth_token")
    depth = await broker_data.get_market_depth("TESTSYMBOL", "NSE")

    assert depth is None
    mock_httpx_client.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.data.get_token", return_value="12345")
@patch("app.web.broker.broker.fivepaisa.api.data.get_br_symbol", return_value="MOCK_BR_SYMBOL")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange", return_value="NSE")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange_type", return_value="C")
async def test_get_market_depth_empty_data(
    mock_map_exchange_type,
    mock_map_exchange,
    mock_get_br_symbol,
    mock_get_token,
    mock_httpx_client,
    mock_settings,
):
    """Test get_market_depth when API returns empty MarketDepthData."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {"MarketDepthData": []},
    }
    mock_httpx_client.post.return_value = mock_response

    broker_data = BrokerData("mock_auth_token")
    depth = await broker_data.get_market_depth("TESTSYMBOL", "NSE")

    assert depth == {"bid": 0, "ask": 0}
    mock_httpx_client.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.data.get_token", return_value="12345")
@patch("app.web.broker.broker.fivepaisa.api.data.get_br_symbol", return_value="MOCK_BR_SYMBOL")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange", return_value="NSE")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange_type", return_value="C")
async def test_get_market_depth_no_bid_or_ask(
    mock_map_exchange_type,
    mock_map_exchange,
    mock_get_br_symbol,
    mock_get_token,
    mock_httpx_client,
    mock_settings,
):
    """Test get_market_depth when no bid or ask data is present."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {
            "MarketDepthData": [
                {"Price": "100.00", "Quantity": "100", "BbBuySellFlag": 1},  # Neither bid nor ask
            ]
        },
    }
    mock_httpx_client.post.return_value = mock_response

    broker_data = BrokerData("mock_auth_token")
    depth = await broker_data.get_market_depth("TESTSYMBOL", "NSE")

    assert depth == {"bid": 0, "ask": 0}
    mock_httpx_client.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.data.get_token", return_value="12345")
@patch("app.web.broker.broker.fivepaisa.api.data.get_br_symbol", return_value="MOCK_BR_SYMBOL")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange", return_value="NSE")
@patch("app.web.broker.broker.fivepaisa.api.data.map_exchange_type", return_value="C")
async def test_get_market_depth_exception_handling(
    mock_map_exchange_type,
    mock_map_exchange,
    mock_get_br_symbol,
    mock_get_token,
    mock_httpx_client,
    mock_settings,
):
    """Test get_market_depth exception handling."""
    mock_httpx_client.post.side_effect = Exception("Network error")

    broker_data = BrokerData("mock_auth_token")
    depth = await broker_data.get_market_depth("TESTSYMBOL", "NSE")

    assert depth is None
    mock_httpx_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_get_depth_success(mock_httpx_client, mock_settings):
    """Test successful retrieval of depth data."""
    broker_data = BrokerData("mock_auth_token")
    with patch(
        "app.web.broker.broker.fivepaisa.api.data.BrokerData.get_market_depth",
        return_value={"bid": 100.00, "ask": 101.00},
    ) as mock_get_market_depth:
        depth = await broker_data.get_depth("TESTSYMBOL", "NSE")

        assert depth == {"bid": 100.00, "ask": 101.00}
        mock_get_market_depth.assert_called_once_with("TESTSYMBOL", "NSE")


@pytest.mark.asyncio
async def test_get_depth_no_market_depth(mock_httpx_client, mock_settings):
    """Test get_depth when get_market_depth returns None."""
    broker_data = BrokerData("mock_auth_token")
    with patch(
        "app.web.broker.broker.fivepaisa.api.data.BrokerData.get_market_depth",
        return_value=None,
    ) as mock_get_market_depth:
        depth = await broker_data.get_depth("TESTSYMBOL", "NSE")

        assert depth is None
        mock_get_market_depth.assert_called_once_with("TESTSYMBOL", "NSE")


@pytest.mark.asyncio
async def test_get_depth_exception_handling(mock_httpx_client, mock_settings):
    """Test get_depth exception handling."""
    broker_data = BrokerData("mock_auth_token")
    with patch(
        "app.web.broker.broker.fivepaisa.api.data.BrokerData.get_market_depth",
        side_effect=Exception("Error getting market depth"),
    ) as mock_get_market_depth:
        depth = await broker_data.get_depth("TESTSYMBOL", "NSE")

        assert depth is None
        mock_get_market_depth.assert_called_once_with("TESTSYMBOL", "NSE")


@pytest.mark.parametrize(
    "interval, expected",
    [
        ("1minute", "1"),
        ("3minute", "3"),
        ("5minute", "5"),
        ("10minute", "10"),
        ("15minute", "15"),
        ("30minute", "30"),
        ("60minute", "60"),
        ("1day", "360"),
        ("1week", "W"),
        ("1month", "M"),
        ("invalid", "30"),  # Default to 30 minutes
    ],
)
def test_map_interval(interval, expected):
    """Test mapping of OpenAlgo interval to Fivepaisa interval."""
    assert map_interval(interval) == expected


def test_process_raw_candles_success():
    """Test successful processing of raw candle data."""
    broker_data = BrokerData("mock_auth_token")
    raw_candles = [
        {"Time": "2023-01-01T09:15:00", "Open": 100, "High": 105, "Low": 99, "Close": 104, "Volume": 1000},
        {"Time": "2023-01-01T09:20:00", "Open": 104, "High": 108, "Low": 103, "Close": 107, "Volume": 1200},
    ]
    processed_candles = broker_data._process_raw_candles(raw_candles)

    assert len(processed_candles) == 2
    assert processed_candles[0]["date"] == "2023-01-01 09:15:00"
    assert processed_candles[0]["open"] == 100
    assert processed_candles[0]["high"] == 105
    assert processed_candles[0]["low"] == 99
    assert processed_candles[0]["close"] == 104
    assert processed_candles[0]["volume"] == 1000


def test_process_raw_candles_empty_input():
    """Test processing with empty raw candle data."""
    broker_data = BrokerData("mock_auth_token")
    raw_candles = []
    processed_candles = broker_data._process_raw_candles(raw_candles)

    assert processed_candles == []


def test_process_raw_candles_missing_keys():
    """Test processing with missing keys in raw candle data."""
    broker_data = BrokerData("mock_auth_token")
    raw_candles = [
        {"Time": "2023-01-01T09:15:00", "Open": 100, "High": 105, "Low": 99, "Volume": 1000},  # Close missing
    ]
    processed_candles = broker_data._process_raw_candles(raw_candles)

    assert len(processed_candles) == 1
    assert processed_candles[0]["close"] == 0  # Default value


# --- Tests for order_api.py ---


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_api_response")
async def test_get_order_book_success(mock_get_api_response):
    """Test successful retrieval of order book."""
    mock_get_api_response.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {"OrderBookDetail": [{"order": "details"}]},
    }
    auth_token = "mock_auth_token"
    order_book = await get_order_book(auth_token)

    assert order_book == {"head": {"statusDescription": "Success"}, "body": {"OrderBookDetail": [{"order": "details"}]}}
    mock_get_api_response.assert_called_once_with(
        "/VendorsAPI/Service1.svc/V3/OrderBook", auth_token, method="POST", payload=ANY
    )


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_api_response")
async def test_get_order_book_api_error(mock_get_api_response):
    """Test get_order_book when API call raises an exception."""
    mock_get_api_response.side_effect = Exception("API error")
    auth_token = "mock_auth_token"

    with pytest.raises(Exception) as exc_info:
        await get_order_book(auth_token)

    assert "API error" in str(exc_info.value)
    mock_get_api_response.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_api_response")
async def test_get_trade_book_success(mock_get_api_response):
    """Test successful retrieval of trade book."""
    mock_get_api_response.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {"TradeBookDetail": [{"trade": "details"}]},
    }
    auth_token = "mock_auth_token"
    trade_book = await get_trade_book(auth_token)

    assert trade_book == {"head": {"statusDescription": "Success"}, "body": {"TradeBookDetail": [{"trade": "details"}]}}
    mock_get_api_response.assert_called_once_with(
        "/VendorsAPI/Service1.svc/V1/TradeBook", auth_token, method="POST", payload=ANY
    )


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_api_response")
async def test_get_trade_book_api_error(mock_get_api_response):
    """Test get_trade_book when API call raises an exception."""
    mock_get_api_response.side_effect = Exception("API error")
    auth_token = "mock_auth_token"

    with pytest.raises(Exception) as exc_info:
        await get_trade_book(auth_token)

    assert "API error" in str(exc_info.value)
    mock_get_api_response.assert_called_once()


# --- Tests for BrokerData.get_history ---


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.data.get_api_response")
@patch("app.web.broker.broker.fivepaisa.api.data.map_interval", return_value="30")
@patch("app.web.broker.broker.fivepaisa.api.data.get_token", return_value="mock_token")
@patch("app.web.broker.broker.fivepaisa.api.data.get_br_symbol", return_value="MOCK_BR_SYMBOL")
async def test_get_history_success(
    mock_get_br_symbol,
    mock_get_token,
    mock_map_interval,
    mock_get_api_response,
    mock_settings,
):
    """Test successful retrieval of historical data."""
    mock_get_api_response.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {
            "Data": [
                {"Time": "2023-01-01T09:15:00", "Open": 100, "High": 105, "Low": 99, "Close": 104, "Volume": 1000},
                {"Time": "2023-01-01T09:20:00", "Open": 104, "High": 108, "Low": 103, "Close": 107, "Volume": 1200},
            ]
        },
    }
    broker_data = BrokerData("mock_auth_token")
    with patch(
        "app.web.broker.broker.fivepaisa.api.data.BrokerData._process_raw_candles",
        return_value=[
            {"date": "2023-01-01 09:15:00", "open": 100, "high": 105, "low": 99, "close": 104, "volume": 1000},
            {"date": "2023-01-01 09:20:00", "open": 104, "high": 108, "low": 103, "close": 107, "volume": 1200},
        ],
    ) as mock_process_raw_candles:
        history_data = await broker_data.get_history("TESTSYMBOL", "NSE", "1minute", 10)

        assert len(history_data) == 2
        assert history_data[0]["close"] == 104
        mock_get_api_response.assert_called_once()
        mock_process_raw_candles.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.data.get_api_response")
@patch("app.web.broker.broker.fivepaisa.api.data.map_interval", return_value="30")
@patch("app.web.broker.broker.fivepaisa.api.data.get_token", return_value="mock_token")
@patch("app.web.broker.broker.fivepaisa.api.data.get_br_symbol", return_value="MOCK_BR_SYMBOL")
async def test_get_history_api_failure(
    mock_get_br_symbol,
    mock_get_token,
    mock_map_interval,
    mock_get_api_response,
    mock_settings,
):
    """Test get_history when API returns failure status."""
    mock_get_api_response.return_value = {
        "head": {"statusDescription": "Failure"},
        "body": {"Data": []},
    }
    broker_data = BrokerData("mock_auth_token")
    history_data = await broker_data.get_history("TESTSYMBOL", "NSE", "1minute", 10)

    assert history_data is None
    mock_get_api_response.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.data.get_api_response")
@patch("app.web.broker.broker.fivepaisa.api.data.map_interval", return_value="30")
@patch("app.web.broker.broker.fivepaisa.api.data.get_token", return_value="mock_token")
@patch("app.web.broker.broker.fivepaisa.api.data.get_br_symbol", return_value="MOCK_BR_SYMBOL")
async def test_get_history_empty_data(
    mock_get_br_symbol,
    mock_get_token,
    mock_map_interval,
    mock_get_api_response,
    mock_settings,
):
    """Test get_history when API returns empty Data."""
    mock_get_api_response.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {"Data": []},
    }
    broker_data = BrokerData("mock_auth_token")
    history_data = await broker_data.get_history("TESTSYMBOL", "NSE", "1minute", 10)

    assert history_data == []
    mock_get_api_response.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.data.get_api_response")
@patch("app.web.broker.broker.fivepaisa.api.data.map_interval", return_value="30")
@patch("app.web.broker.broker.fivepaisa.api.data.get_token", return_value="mock_token")
@patch("app.web.broker.broker.fivepaisa.api.data.get_br_symbol", return_value="MOCK_BR_SYMBOL")
async def test_get_history_exception_handling(
    mock_get_br_symbol,
    mock_get_token,
    mock_map_interval,
    mock_get_api_response,
    mock_settings,
):
    """Test get_history exception handling."""
    mock_get_api_response.side_effect = Exception("API error")
    broker_data = BrokerData("mock_auth_token")
    history_data = await broker_data.get_history("TESTSYMBOL", "NSE", "1minute", 10)

    assert history_data is None
    mock_get_api_response.assert_called_once()


# --- Tests for BrokerData.fix_timestamps ---


def test_fix_timestamps_success():
    """Test successful fixing of timestamps."""
    broker_data = BrokerData("mock_auth_token")
    raw_candles = [
        {"time": "2023-01-01T09:15:00", "open": 100},
        {"time": "2023-01-01T09:20:00", "open": 104},
    ]
    fixed_candles = broker_data.fix_timestamps(raw_candles)

    assert len(fixed_candles) == 2
    assert fixed_candles[0]["time"] == pd.Timestamp("2023-01-01 09:15:00+0530", tz="Asia/Calcutta")
    assert fixed_candles[1]["time"] == pd.Timestamp("2023-01-01 09:20:00+0530", tz="Asia/Calcutta")


def test_fix_timestamps_empty_input():
    """Test fixing timestamps with empty input."""
    broker_data = BrokerData("mock_auth_token")
    raw_candles = []
    fixed_candles = broker_data.fix_timestamps(raw_candles)

    assert fixed_candles == []


def test_fix_timestamps_missing_time_key():
    """Test fixing timestamps with missing 'time' key."""
    broker_data = BrokerData("mock_auth_token")
    raw_candles = [{"open": 100}]  # Missing 'time' key
    fixed_candles = broker_data.fix_timestamps(raw_candles)

    assert len(fixed_candles) == 1
    assert "time" not in fixed_candles[0]


# --- Tests for BrokerData.get_supported_intervals ---


def test_get_supported_intervals():
    """Test retrieval of supported intervals."""
    broker_data = BrokerData("mock_auth_token")
    intervals = broker_data.get_supported_intervals()

    expected_intervals = [
        "1minute",
        "3minute",
        "5minute",
        "10minute",
        "15minute",
        "30minute",
        "60minute",
        "1day",
        "1week",
        "1month",
    ]
    assert intervals == expected_intervals


# --- Tests for order_api.py ---


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_api_response")
async def test_get_order_book_success(mock_get_api_response):
    """Test successful retrieval of order book."""
    mock_get_api_response.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {"OrderBookDetail": [{"order": "details"}]},
    }
    auth_token = "mock_auth_token"
    order_book = await get_order_book(auth_token)

    assert order_book == {"head": {"statusDescription": "Success"}, "body": {"OrderBookDetail": [{"order": "details"}]}}
    mock_get_api_response.assert_called_once_with(
        "/VendorsAPI/Service1.svc/V3/OrderBook", auth_token, method="POST", payload=ANY
    )


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_api_response")
async def test_get_order_book_api_error(mock_get_api_response):
    """Test get_order_book when API call raises an exception."""
    mock_get_api_response.side_effect = Exception("API error")
    auth_token = "mock_auth_token"

    with pytest.raises(Exception) as exc_info:
        await get_order_book(auth_token)

    assert "API error" in str(exc_info.value)
    mock_get_api_response.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_api_response")
async def test_get_trade_book_success(mock_get_api_response):
    """Test successful retrieval of trade book."""
    mock_get_api_response.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {"TradeBookDetail": [{"trade": "details"}]},
    }
    auth_token = "mock_auth_token"
    trade_book = await get_trade_book(auth_token)

    assert trade_book == {"head": {"statusDescription": "Success"}, "body": {"TradeBookDetail": [{"trade": "details"}]}}
    mock_get_api_response.assert_called_once_with(
        "/VendorsAPI/Service1.svc/V1/TradeBook", auth_token, method="POST", payload=ANY
    )


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_api_response")
async def test_get_trade_book_api_error(mock_get_api_response):
    """Test get_trade_book when API call raises an exception."""
    mock_get_api_response.side_effect = Exception("API error")
    auth_token = "mock_auth_token"

    with pytest.raises(Exception) as exc_info:
        await get_trade_book(auth_token)

    assert "API error" in str(exc_info.value)
    mock_get_api_response.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
async def test_get_positions_success(mock_get_httpx_client):
    """Test successful retrieval of positions."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {"NetPositionDetail": [{"position": "details"}]},
    }
    mock_get_httpx_client.return_value.post.return_value = mock_response

    auth_token = "mock_auth_token"
    positions = await get_positions(auth_token)

    assert positions == {
        "head": {"statusDescription": "Success"},
        "body": {"NetPositionDetail": [{"position": "details"}]},
    }
    mock_get_httpx_client.return_value.post.assert_called_once_with(
        f"{settings.FIVEPAISA_BASE_URL}/VendorsAPI/Service1.svc/V2/NetPositionNetWise",
        content=ANY,
        headers=ANY,
        timeout=60.0,
    )


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
async def test_get_positions_timeout_and_retry(mock_get_httpx_client):
    """Test handling of timeout with retries for positions."""
    mock_get_httpx_client.return_value.post.side_effect = httpx.TimeoutException("Request timed out")

    auth_token = "mock_auth_token"
    positions = await get_positions(auth_token)

    assert positions == {"body": {"NetPositionDetail": []}}
    assert mock_get_httpx_client.return_value.post.call_count == 3  # 3 retries


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
async def test_get_positions_http_error(mock_get_httpx_client):
    """Test handling of HTTPStatusError for positions."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=MagicMock(status_code=400, text="Bad Request")
    )
    mock_get_httpx_client.return_value.post.return_value = mock_response

    auth_token = "mock_auth_token"
    positions = await get_positions(auth_token)

    assert positions == {"body": {"NetPositionDetail": []}}
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
async def test_get_positions_general_exception(mock_get_httpx_client):
    """Test handling of general exception for positions."""
    mock_get_httpx_client.return_value.post.side_effect = Exception("Something went wrong")

    auth_token = "mock_auth_token"
    positions = await get_positions(auth_token)

    assert positions == {"body": {"NetPositionDetail": []}}
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
async def test_get_holdings_success(mock_get_httpx_client):
    """Test successful retrieval of holdings."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {"HoldingsDetail": [{"holding": "details"}]},
    }
    mock_get_httpx_client.return_value.post.return_value = mock_response

    auth_token = "mock_auth_token"
    holdings = await get_holdings(auth_token)

    assert holdings == {
        "head": {"statusDescription": "Success"},
        "body": {"HoldingsDetail": [{"holding": "details"}]},
    }
    mock_get_httpx_client.return_value.post.assert_called_once_with(
        f"{settings.FIVEPAISA_BASE_URL}/VendorsAPI/Service1.svc/V2/Holding",
        content=ANY,
        headers=ANY,
        timeout=60.0,
    )


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
async def test_get_holdings_timeout_and_retry(mock_get_httpx_client):
    """Test handling of timeout with retries for holdings."""
    mock_get_httpx_client.return_value.post.side_effect = httpx.TimeoutException("Request timed out")

    auth_token = "mock_auth_token"
    holdings = await get_holdings(auth_token)

    assert holdings == {"body": {"HoldingsDetail": []}}
    assert mock_get_httpx_client.return_value.post.call_count == 3  # 3 retries


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
async def test_get_holdings_http_error(mock_get_httpx_client):
    """Test handling of HTTPStatusError for holdings."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=MagicMock(status_code=400, text="Bad Request")
    )
    mock_get_httpx_client.return_value.post.return_value = mock_response

    auth_token = "mock_auth_token"
    holdings = await get_holdings(auth_token)

    assert holdings == {"body": {"HoldingsDetail": []}}
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
async def test_get_holdings_general_exception(mock_get_httpx_client):
    """Test handling of general exception for holdings."""
    mock_get_httpx_client.return_value.post.side_effect = Exception("Something went wrong")

    auth_token = "mock_auth_token"
    holdings = await get_holdings(auth_token)

    assert holdings == {"body": {"HoldingsDetail": []}}
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_place_order_api_success(mock_transform_data, mock_get_httpx_client):
    """Test successful placement of an order."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {"BrokerOrderID": "mock_order_id"},
    }
    mock_get_httpx_client.return_value.post.return_value = mock_response

    order_data = {"symbol": "TEST", "exchange": "NSE"}
    auth_token = "mock_auth_token"
    response, response_data, order_id = await place_order_api(order_data, auth_token)

    assert response.status_code == 200
    assert response_data == {"head": {"statusDescription": "Success"}, "body": {"BrokerOrderID": "mock_order_id"}}
    assert order_id == "mock_order_id"
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once_with(
        f"{settings.FIVEPAISA_BASE_URL}/VendorsAPI/Service1.svc/V3/PlaceOrder",
        content=json.dumps({"ClientCode": settings.BROKER_API_KEY.split(':::')[1], **mock_transform_data.return_value}),
        headers=ANY,
        timeout=60.0,
    )


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_place_order_api_failure(mock_transform_data, mock_get_httpx_client):
    """Test placement of an order with API failure."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Failure"},
        "body": {"Message": "Invalid order"},
    }
    mock_get_httpx_client.return_value.post.return_value = mock_response

    order_data = {"symbol": "TEST", "exchange": "NSE"}
    auth_token = "mock_auth_token"
    response, response_data, order_id = await place_order_api(order_data, auth_token)

    assert response.status_code == 200
    assert response_data == {"head": {"statusDescription": "Failure"}, "body": {"Message": "Invalid order"}}
    assert order_id is None
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_place_order_api_http_error(mock_transform_data, mock_get_httpx_client):
    """Test HTTPStatusError during order placement."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=MagicMock(status_code=400, text="Bad Request")
    )
    mock_get_httpx_client.return_value.post.return_value = mock_response

    order_data = {"symbol": "TEST", "exchange": "NSE"}
    auth_token = "mock_auth_token"
    response, response_data, order_id = await place_order_api(order_data, auth_token)

    assert response is None
    assert response_data == {"error": "HTTP error occurred: 400"}
    assert order_id is None
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_place_order_api_request_error(mock_transform_data, mock_get_httpx_client):
    """Test httpx.RequestError during order placement."""
    mock_get_httpx_client.return_value.post.side_effect = httpx.RequestError("Network error", request=MagicMock())

    order_data = {"symbol": "TEST", "exchange": "NSE"}
    auth_token = "mock_auth_token"
    response, response_data, order_id = await place_order_api(order_data, auth_token)

    assert response is None
    assert response_data == {"error": "Request error occurred: Network error"}
    assert order_id is None
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_place_order_api_general_exception(mock_transform_data, mock_get_httpx_client):
    """Test general exception during order placement."""
    mock_get_httpx_client.return_value.post.side_effect = Exception("Something went wrong")

    order_data = {"symbol": "TEST", "exchange": "NSE"}
    auth_token = "mock_auth_token"
    response, response_data, order_id = await place_order_api(order_data, auth_token)

    assert response is None
    assert response_data == {"error": "An error occurred: Something went wrong"}
    assert order_id is None
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_place_smartorder_api_success(mock_transform_data, mock_get_httpx_client):
    """Test successful placement of a smart order."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {"BrokerOrderID": "mock_smart_order_id"},
    }
    mock_get_httpx_client.return_value.post.return_value = mock_response

    order_data = {"symbol": "TEST", "exchange": "NSE"}
    auth_token = "mock_auth_token"
    response, response_data, order_id = await place_smartorder_api(order_data, auth_token)

    assert response.status_code == 200
    assert response_data == {"head": {"statusDescription": "Success"}, "body": {"BrokerOrderID": "mock_smart_order_id"}}
    assert order_id == "mock_smart_order_id"
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once_with(
        f"{settings.FIVEPAISA_BASE_URL}/VendorsAPI/Service1.svc/V3/PlaceOrder",
        content=json.dumps({"ClientCode": settings.BROKER_API_KEY.split(':::')[1], **mock_transform_data.return_value}),
        headers=ANY,
        timeout=60.0,
    )


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_place_smartorder_api_failure(mock_transform_data, mock_get_httpx_client):
    """Test placement of a smart order with API failure."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Failure"},
        "body": {"Message": "Invalid smart order"},
    }
    mock_get_httpx_client.return_value.post.return_value = mock_response

    order_data = {"symbol": "TEST", "exchange": "NSE"}
    auth_token = "mock_auth_token"
    response, response_data, order_id = await place_smartorder_api(order_data, auth_token)

    assert response.status_code == 200
    assert response_data == {"head": {"statusDescription": "Failure"}, "body": {"Message": "Invalid smart order"}}
    assert order_id is None
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_place_smartorder_api_http_error(mock_transform_data, mock_get_httpx_client):
    """Test HTTPStatusError during smart order placement."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=MagicMock(status_code=400, text="Bad Request")
    )
    mock_get_httpx_client.return_value.post.return_value = mock_response

    order_data = {"symbol": "TEST", "exchange": "NSE"}
    auth_token = "mock_auth_token"
    response, response_data, order_id = await place_smartorder_api(order_data, auth_token)

    assert response is None
    assert response_data == {"error": "HTTP error occurred: 400"}
    assert order_id is None
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_place_smartorder_api_request_error(mock_transform_data, mock_get_httpx_client):
    """Test httpx.RequestError during smart order placement."""
    mock_get_httpx_client.return_value.post.side_effect = httpx.RequestError("Network error", request=MagicMock())

    order_data = {"symbol": "TEST", "exchange": "NSE"}
    auth_token = "mock_auth_token"
    response, response_data, order_id = await place_smartorder_api(order_data, auth_token)

    assert response is None
    assert response_data == {"error": "Request error occurred: Network error"}
    assert order_id is None
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_close_all_positions_success(mock_transform_data, mock_get_httpx_client):
    """Test successful closing of all positions."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {"Message": "All positions closed"},
    }
    mock_get_httpx_client.return_value.post.return_value = mock_response

    order_data = {"product_type": "C", "exchange": "NSE"}
    auth_token = "mock_auth_token"
    response, response_data = await close_all_positions(order_data, auth_token)

    assert response.status_code == 200
    assert response_data == {"head": {"statusDescription": "Success"}, "body": {"Message": "All positions closed"}}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once_with(
        f"{settings.FIVEPAISA_BASE_URL}/VendorsAPI/Service1.svc/V3/TradeExit",
        content=json.dumps({"ClientCode": settings.BROKER_API_KEY.split(':::')[1], **mock_transform_data.return_value}),
        headers=ANY,
        timeout=60.0,
    )


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_close_all_positions_failure(mock_transform_data, mock_get_httpx_client):
    """Test closing all positions with API failure."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Failure"},
        "body": {"Message": "Failed to close positions"},
    }
    mock_get_httpx_client.return_value.post.return_value = mock_response

    order_data = {"product_type": "C", "exchange": "NSE"}
    auth_token = "mock_auth_token"
    response, response_data = await close_all_positions(order_data, auth_token)

    assert response.status_code == 200
    assert response_data == {"head": {"statusDescription": "Failure"}, "body": {"Message": "Failed to close positions"}}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_close_all_positions_http_error(mock_transform_data, mock_get_httpx_client):
    """Test HTTPStatusError during closing all positions."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=MagicMock(status_code=400, text="Bad Request")
    )
    mock_get_httpx_client.return_value.post.return_value = mock_response

    order_data = {"product_type": "C", "exchange": "NSE"}
    auth_token = "mock_auth_token"
    response, response_data = await close_all_positions(order_data, auth_token)

    assert response is None
    assert response_data == {"error": "HTTP error occurred: 400"}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_cancel_order_success(mock_transform_data, mock_get_httpx_client):
    """Test successful cancellation of an order."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {"Message": "Order cancelled successfully"},
    }
    mock_get_httpx_client.return_value.post.return_value = mock_response

    order_data = {"order_id": "mock_order_id"}
    auth_token = "mock_auth_token"
    response, response_data = await cancel_order(order_data, auth_token)

    assert response.status_code == 200
    assert response_data == {"head": {"statusDescription": "Success"}, "body": {"Message": "Order cancelled successfully"}}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once_with(
        f"{settings.FIVEPAISA_BASE_URL}/VendorsAPI/Service1.svc/V3/CancelOrder",
        content=json.dumps({"ClientCode": settings.BROKER_API_KEY.split(':::')[1], **mock_transform_data.return_value}),
        headers=ANY,
        timeout=60.0,
    )


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_cancel_order_failure(mock_transform_data, mock_get_httpx_client):
    """Test cancellation of an order with API failure."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Failure"},
        "body": {"Message": "Failed to cancel order"},
    }
    mock_get_httpx_client.return_value.post.return_value = mock_response

    order_data = {"order_id": "mock_order_id"}
    auth_token = "mock_auth_token"
    response, response_data = await cancel_order(order_data, auth_token)

    assert response.status_code == 200
    assert response_data == {"head": {"statusDescription": "Failure"}, "body": {"Message": "Failed to cancel order"}}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_cancel_order_http_error(mock_transform_data, mock_get_httpx_client):
    """Test HTTPStatusError during order cancellation."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=MagicMock(status_code=400, text="Bad Request")
    )
    mock_get_httpx_client.return_value.post.return_value = mock_response

    order_data = {"order_id": "mock_order_id"}
    auth_token = "mock_auth_token"
    response, response_data = await cancel_order(order_data, auth_token)

    assert response is None
    assert response_data == {"error": "HTTP error occurred: 400"}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_modify_order_success(mock_transform_data, mock_get_httpx_client):
    """Test successful modification of an order."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {"Message": "Order modified successfully"},
    }
    mock_get_httpx_client.return_value.post.return_value = mock_response

    order_data = {"order_id": "mock_order_id", "quantity": 10}
    auth_token = "mock_auth_token"
    response, response_data = await modify_order(order_data, auth_token)

    assert response.status_code == 200
    assert response_data == {"head": {"statusDescription": "Success"}, "body": {"Message": "Order modified successfully"}}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once_with(
        f"{settings.FIVEPAISA_BASE_URL}/VendorsAPI/Service1.svc/V3/ModifyOrder",
        content=json.dumps({"ClientCode": settings.BROKER_API_KEY.split(':::')[1], **mock_transform_data.return_value}),
        headers=ANY,
        timeout=60.0,
    )


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_modify_order_failure(mock_transform_data, mock_get_httpx_client):
    """Test modification of an order with API failure."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Failure"},
        "body": {"Message": "Failed to modify order"},
    }
    mock_get_httpx_client.return_value.post.return_value = mock_response

    order_data = {"order_id": "mock_order_id", "quantity": 10}
    auth_token = "mock_auth_token"
    response, response_data = await modify_order(order_data, auth_token)

    assert response.status_code == 200
    assert response_data == {"head": {"statusDescription": "Failure"}, "body": {"Message": "Failed to modify order"}}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_modify_order_http_error(mock_transform_data, mock_get_httpx_client):
    """Test HTTPStatusError during order modification."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=MagicMock(status_code=400, text="Bad Request")
    )
    mock_get_httpx_client.return_value.post.return_value = mock_response

    order_data = {"order_id": "mock_order_id", "quantity": 10}
    auth_token = "mock_auth_token"
    response, response_data = await modify_order(order_data, auth_token)

    assert response is None
    assert response_data == {"error": "HTTP error occurred: 400"}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_cancel_all_orders_api_success(mock_transform_data, mock_get_httpx_client):
    """Test successful cancellation of all orders."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {"Message": "All orders cancelled successfully"},
    }
    mock_get_httpx_client.return_value.post.return_value = mock_response

    order_data = {"product_type": "C"}
    auth_token = "mock_auth_token"
    response, response_data = await cancel_all_orders_api(order_data, auth_token)

    assert response.status_code == 200
    assert response_data == {"head": {"statusDescription": "Success"}, "body": {"Message": "All orders cancelled successfully"}}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once_with(
        f"{settings.FIVEPAISA_BASE_URL}/VendorsAPI/Service1.svc/V3/TradeExit",
        content=json.dumps({"ClientCode": settings.BROKER_API_KEY.split(':::')[1], **mock_transform_data.return_value}),
        headers=ANY,
        timeout=60.0,
    )


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_cancel_all_orders_api_failure(mock_transform_data, mock_get_httpx_client):
    """Test cancellation of all orders with API failure."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Failure"},
        "body": {"Message": "Failed to cancel all orders"},
    }
    mock_get_httpx_client.return_value.post.return_value = mock_response

    order_data = {"product_type": "C"}
    auth_token = "mock_auth_token"
    response, response_data = await cancel_all_orders_api(order_data, auth_token)

    assert response.status_code == 200
    assert response_data == {"head": {"statusDescription": "Failure"}, "body": {"Message": "Failed to cancel all orders"}}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_cancel_all_orders_api_http_error(mock_transform_data, mock_get_httpx_client):
    """Test HTTPStatusError during cancellation of all orders."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=MagicMock(status_code=400, text="Bad Request")
    )
    mock_get_httpx_client.return_value.post.return_value = mock_response

    order_data = {"product_type": "C"}
    auth_token = "mock_auth_token"
    response, response_data = await cancel_all_orders_api(order_data, auth_token)

    assert response is None
    assert response_data == {"error": "HTTP error occurred: 400"}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_cancel_all_orders_api_request_error(mock_transform_data, mock_get_httpx_client):
    """Test httpx.RequestError during cancellation of all orders."""
    mock_get_httpx_client.return_value.post.side_effect = httpx.RequestError("Network error", request=MagicMock())

    order_data = {"product_type": "C"}
    auth_token = "mock_auth_token"
    response, response_data = await cancel_all_orders_api(order_data, auth_token)

    assert response is None
    assert response_data == {"error": "Request error occurred: Network error"}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_cancel_all_orders_api_general_exception(mock_transform_data, mock_get_httpx_client):
    """Test general exception during cancellation of all orders."""
    mock_get_httpx_client.return_value.post.side_effect = Exception("Something went wrong")

    order_data = {"product_type": "C"}
    auth_token = "mock_auth_token"
    response, response_data = await cancel_all_orders_api(order_data, auth_token)

    assert response is None
    assert response_data == {"error": "An error occurred: Something went wrong"}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_modify_order_request_error(mock_transform_data, mock_get_httpx_client):
    """Test httpx.RequestError during order modification."""
    mock_get_httpx_client.return_value.post.side_effect = httpx.RequestError("Network error", request=MagicMock())

    order_data = {"order_id": "mock_order_id", "quantity": 10}
    auth_token = "mock_auth_token"
    response, response_data = await modify_order(order_data, auth_token)

    assert response is None
    assert response_data == {"error": "Request error occurred: Network error"}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_modify_order_general_exception(mock_transform_data, mock_get_httpx_client):
    """Test general exception during order modification."""
    mock_get_httpx_client.return_value.post.side_effect = Exception("Something went wrong")

    order_data = {"order_id": "mock_order_id", "quantity": 10}
    auth_token = "mock_auth_token"
    response, response_data = await modify_order(order_data, auth_token)

    assert response is None
    assert response_data == {"error": "An error occurred: Something went wrong"}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_cancel_order_request_error(mock_transform_data, mock_get_httpx_client):
    """Test httpx.RequestError during order cancellation."""
    mock_get_httpx_client.return_value.post.side_effect = httpx.RequestError("Network error", request=MagicMock())

    order_data = {"order_id": "mock_order_id"}
    auth_token = "mock_auth_token"
    response, response_data = await cancel_order(order_data, auth_token)

    assert response is None
    assert response_data == {"error": "Request error occurred: Network error"}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_cancel_order_general_exception(mock_transform_data, mock_get_httpx_client):
    """Test general exception during order cancellation."""
    mock_get_httpx_client.return_value.post.side_effect = Exception("Something went wrong")

    order_data = {"order_id": "mock_order_id"}
    auth_token = "mock_auth_token"
    response, response_data = await cancel_order(order_data, auth_token)

    assert response is None
    assert response_data == {"error": "An error occurred: Something went wrong"}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_close_all_positions_request_error(mock_transform_data, mock_get_httpx_client):
    """Test httpx.RequestError during closing all positions."""
    mock_get_httpx_client.return_value.post.side_effect = httpx.RequestError("Network error", request=MagicMock())

    order_data = {"product_type": "C", "exchange": "NSE"}
    auth_token = "mock_auth_token"
    response, response_data = await close_all_positions(order_data, auth_token)

    assert response is None
    assert response_data == {"error": "Request error occurred: Network error"}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_close_all_positions_general_exception(mock_transform_data, mock_get_httpx_client):
    """Test general exception during closing all positions."""
    mock_get_httpx_client.return_value.post.side_effect = Exception("Something went wrong")

    order_data = {"product_type": "C", "exchange": "NSE"}
    auth_token = "mock_auth_token"
    response, response_data = await close_all_positions(order_data, auth_token)

    assert response is None
    assert response_data == {"error": "An error occurred: Something went wrong"}
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
@patch("app.web.broker.broker.fivepaisa.api.order_api.transform_data", return_value={"mock": "transformed_data"})
async def test_place_smartorder_api_general_exception(mock_transform_data, mock_get_httpx_client):
    """Test general exception during smart order placement."""
    mock_get_httpx_client.return_value.post.side_effect = Exception("Something went wrong")

    order_data = {"symbol": "TEST", "exchange": "NSE"}
    auth_token = "mock_auth_token"
    response, response_data, order_id = await place_smartorder_api(order_data, auth_token)

    assert response is None
    assert response_data == {"error": "An error occurred: Something went wrong"}
    assert order_id is None
    mock_transform_data.assert_called_once_with(order_data)
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
async def test_get_open_position_success(mock_get_httpx_client):
    """Test successful retrieval of open positions."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {"TradeBookDetail": [{"open_position": "details"}]},
    }
    mock_get_httpx_client.return_value.post.return_value = mock_response

    auth_token = "mock_auth_token"
    open_positions = await get_open_position(auth_token)

    assert open_positions == {
        "head": {"statusDescription": "Success"},
        "body": {"TradeBookDetail": [{"open_position": "details"}]},
    }
    mock_get_httpx_client.return_value.post.assert_called_once_with(
        f"{settings.FIVEPAISA_BASE_URL}/VendorsAPI/Service1.svc/V3/TradeBook",
        content=ANY,
        headers=ANY,
        timeout=60.0,
    )


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
async def test_get_open_position_timeout_and_retry(mock_get_httpx_client):
    """Test handling of timeout with retries for open positions."""
    mock_get_httpx_client.return_value.post.side_effect = httpx.TimeoutException("Request timed out")

    auth_token = "mock_auth_token"
    open_positions = await get_open_position(auth_token)

    assert open_positions == {"body": {"TradeBookDetail": []}}
    assert mock_get_httpx_client.return_value.post.call_count == 3  # 3 retries


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
async def test_get_open_position_http_error(mock_get_httpx_client):
    """Test handling of HTTPStatusError for open positions."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=MagicMock(status_code=400, text="Bad Request")
    )
    mock_get_httpx_client.return_value.post.return_value = mock_response

    auth_token = "mock_auth_token"
    open_positions = await get_open_position(auth_token)

    assert open_positions == {"body": {"TradeBookDetail": []}}
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
async def test_get_open_position_general_exception(mock_get_httpx_client):
    """Test handling of general exception for open positions."""
    mock_get_httpx_client.return_value.post.side_effect = Exception("Something went wrong")

    auth_token = "mock_auth_token"
    open_positions = await get_open_position(auth_token)

    assert open_positions == {"body": {"TradeBookDetail": []}}
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
async def test_get_holdings_success(mock_get_httpx_client):
    """Test successful retrieval of holdings."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "head": {"statusDescription": "Success"},
        "body": {"HoldingsDetail": [{"holding": "details"}]},
    }
    mock_get_httpx_client.return_value.post.return_value = mock_response

    auth_token = "mock_auth_token"
    holdings = await get_holdings(auth_token)

    assert holdings == {
        "head": {"statusDescription": "Success"},
        "body": {"HoldingsDetail": [{"holding": "details"}]},
    }
    mock_get_httpx_client.return_value.post.assert_called_once_with(
        f"{settings.FIVEPAISA_BASE_URL}/VendorsAPI/Service1.svc/V2/Holding",
        content=ANY,
        headers=ANY,
        timeout=60.0,
    )


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
async def test_get_holdings_timeout_and_retry(mock_get_httpx_client):
    """Test handling of timeout with retries for holdings."""
    mock_get_httpx_client.return_value.post.side_effect = httpx.TimeoutException("Request timed out")

    auth_token = "mock_auth_token"
    holdings = await get_holdings(auth_token)

    assert holdings == {"body": {"HoldingsDetail": []}}
    assert mock_get_httpx_client.return_value.post.call_count == 3  # 3 retries


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
async def test_get_holdings_http_error(mock_get_httpx_client):
    """Test handling of HTTPStatusError for holdings."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=MagicMock(status_code=400, text="Bad Request")
    )
    mock_get_httpx_client.return_value.post.return_value = mock_response

    auth_token = "mock_auth_token"
    holdings = await get_holdings(auth_token)

    assert holdings == {"body": {"HoldingsDetail": []}}
    mock_get_httpx_client.return_value.post.assert_called_once()


@pytest.mark.asyncio
@patch("app.web.broker.broker.fivepaisa.api.order_api.get_httpx_client")
async def test_get_holdings_general_exception(mock_get_httpx_client):
    """Test handling of general exception for holdings."""
    mock_get_httpx_client.return_value.post.side_effect = Exception("Something went wrong")

    auth_token = "mock_auth_token"
    holdings = await get_holdings(auth_token)

    assert holdings == {"body": {"HoldingsDetail": []}}
    mock_get_httpx_client.return_value.post.assert_called_once()