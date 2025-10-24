import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.web.brokers.ibulls.api.auth_api import authenticate_broker, get_feed_token
from app.web.brokers.ibulls.api.data import BrokerData, get_api_response as data_get_api_response
from app.web.brokers.ibulls.api.order_api import (
    cancel_all_orders_api,
    cancel_order,
    close_all_positions,
    get_api_response as order_get_api_response,
    get_holdings,
    get_open_position,
    get_order_book,
    get_positions,
    get_trade_book,
    modify_order,
    place_order_api,
    place_smartorder_api,
)

# --- Fixtures ---

@pytest.fixture
def mock_settings():
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.BROKER_API_KEY = "test_api_key"
        mock_settings.BROKER_API_SECRET = "test_api_secret"
        mock_settings.BROKER_API_KEY_MARKET = "test_market_api_key"
        mock_settings.BROKER_API_SECRET_MARKET = "test_market_api_secret"
        yield mock_settings

@pytest.fixture
def mock_httpx_client():
    with patch("app.utils.httpx_client.get_httpx_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_logger():
    with patch("app.web.broker.broker.ibulls.api.auth_api.logger") as mock_auth_logger, \
         patch("app.web.broker.broker.ibulls.api.data.logger") as mock_data_logger, \
         patch("app.web.broker.broker.ibulls.api.order_api.logger") as mock_order_logger:
        yield mock_auth_logger, mock_data_logger, mock_order_logger

@pytest.fixture
def mock_db_session():
    with patch("app.web.broker.broker.ibulls.api.data.db_session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        yield mock_session_instance

@pytest.fixture
def mock_symtoken():
    with patch("app.web.broker.broker.ibulls.api.data.SymToken") as mock_sym:
        yield mock_sym

@pytest.fixture
def mock_get_br_symbol():
    with patch("app.web.broker.broker.ibulls.api.data.get_br_symbol") as mock_br_symbol, \
         patch("app.web.broker.broker.ibulls.api.order_api.get_br_symbol") as mock_order_br_symbol:
        mock_br_symbol.return_value = "IBULLS_SYMBOL"
        mock_order_br_symbol.return_value = "IBULLS_SYMBOL"
        yield mock_br_symbol

@pytest.fixture
def mock_get_token():
    with patch("app.web.broker.broker.ibulls.api.order_api.get_token") as mock_token:
        mock_token.return_value = "12345"
        yield mock_token

@pytest.fixture
def mock_transform_data():
    with patch("app.web.broker.broker.ibulls.mapping.transform_data") as mock_transform:
        mock_transform.return_value = {"transformed_key": "transformed_value"}
        yield mock_transform

@pytest.fixture
def mock_transform_modify_order_data():
    with patch("app.web.broker.broker.ibulls.mapping.transform_modify_order_data") as mock_transform:
        mock_transform.return_value = {"modified_key": "modified_value"}
        yield mock_transform

@pytest.fixture
def mock_map_product_type():
    with patch("app.web.broker.broker.ibulls.mapping.map_product_type") as mock_map:
        mock_map.return_value = "CNC"
        yield mock_map


# --- Auth API Tests ---

class TestAuthAPI:
    def test_authenticate_broker_success(self, mock_settings, mock_httpx_client, mock_logger):
        mock_client = mock_httpx_client
        mock_client.post.side_effect = [
            MagicMock(status_code=200, json=lambda: {"type": "success", "result": {"token": "auth_token_123"}}),
            MagicMock(status_code=200, json=lambda: {"type": "success", "result": {"token": "feed_token_456", "userID": "user_id_789"}}),
        ]

        token, feed_token, user_id, error = authenticate_broker("request_token_abc")

        assert token == "auth_token_123"
        assert feed_token == "feed_token_456"
        assert user_id == "user_id_789"
        assert error is None
        assert mock_client.post.call_count == 2
        mock_logger[0].info.assert_any_call("Auth Token: auth_token_123")
        mock_logger[0].info.assert_any_call("Feed Token: feed_token_456")

    def test_authenticate_broker_no_auth_token_in_response(self, mock_settings, mock_httpx_client, mock_logger):
        mock_client = mock_httpx_client
        mock_client.post.return_value = MagicMock(status_code=200, json=lambda: {"type": "success", "result": {}})

        token, feed_token, user_id, error = authenticate_broker("request_token_abc")

        assert token is None
        assert feed_token is None
        assert user_id is None
        assert "no access token was returned" in error
        mock_logger[0].info.assert_not_called()

    def test_authenticate_broker_api_error(self, mock_settings, mock_httpx_client, mock_logger):
        mock_client = mock_httpx_client
        mock_client.post.return_value = MagicMock(status_code=400, json=lambda: {"message": "Invalid credentials"})

        token, feed_token, user_id, error = authenticate_broker("request_token_abc")

        assert token is None
        assert feed_token is None
        assert user_id is None
        assert "API error: Invalid credentials" in error
        mock_logger[0].info.assert_not_called()

    def test_authenticate_broker_exception(self, mock_settings, mock_httpx_client, mock_logger):
        mock_client = mock_httpx_client
        mock_client.post.side_effect = Exception("Network error")

        token, feed_token, user_id, error = authenticate_broker("request_token_abc")

        assert token is None
        assert feed_token is None
        assert user_id is None
        assert "Error during authentication: Network error" in error
        mock_logger[0].info.assert_not_called()

    def test_authenticate_broker_feed_token_error(self, mock_settings, mock_httpx_client, mock_logger):
        mock_client = mock_httpx_client
        mock_client.post.side_effect = [
            MagicMock(status_code=200, json=lambda: {"type": "success", "result": {"token": "auth_token_123"}}),
            MagicMock(status_code=400, json=lambda: {"description": "Market data login failed"}),
        ]

        token, feed_token, user_id, error = authenticate_broker("request_token_abc")

        assert token == "auth_token_123"
        assert feed_token is None
        assert user_id is None
        assert "Feed token error: API Error (Feed): Market data login failed" in error
        mock_logger[0].info.assert_any_call("Auth Token: auth_token_123")
        mock_logger[0].info.assert_any_call("Feed token request failed. Please check the response.") # from get_feed_token

    def test_get_feed_token_success(self, mock_settings, mock_httpx_client, mock_logger):
        mock_client = mock_httpx_client
        mock_client.post.return_value = MagicMock(status_code=200, json=lambda: {"type": "success", "result": {"token": "feed_token_456", "userID": "user_id_789"}})

        feed_token, user_id, error = get_feed_token()

        assert feed_token == "feed_token_456"
        assert user_id == "user_id_789"
        assert error is None
        mock_logger[0].info.assert_any_call("Feed Token: feed_token_456")

    def test_get_feed_token_request_failed(self, mock_settings, mock_httpx_client, mock_logger):
        mock_client = mock_httpx_client
        mock_client.post.return_value = MagicMock(status_code=200, json=lambda: {"type": "error", "message": "Login failed"})

        feed_token, user_id, error = get_feed_token()

        assert feed_token is None
        assert user_id is None
        assert "Feed token request failed. Please check the response." in error
        mock_logger[0].info.assert_not_called()

    def test_get_feed_token_api_error(self, mock_settings, mock_httpx_client, mock_logger):
        mock_client = mock_httpx_client
        mock_client.post.return_value = MagicMock(status_code=401, json=lambda: {"description": "Unauthorized"})

        feed_token, user_id, error = get_feed_token()

        assert feed_token is None
        assert user_id is None
        assert "API Error (Feed): Unauthorized" in error
        mock_logger[0].info.assert_not_called()

    def test_get_feed_token_exception(self, mock_settings, mock_httpx_client, mock_logger):
        mock_client = mock_httpx_client
        mock_client.post.side_effect = Exception("Connection refused")

        feed_token, user_id, error = get_feed_token()

        assert feed_token is None
        assert user_id is None
        assert "An exception occurred: Connection refused" in error
        mock_logger[0].info.assert_not_called()


# --- Data API Tests ---

class TestDataAPI:
    def test_get_api_response_post_success(self, mock_httpx_client, mock_logger):
        mock_client = mock_httpx_client
        mock_client.post.return_value = MagicMock(status_code=200, json=lambda: {"type": "success", "data": "some_data"})

        response = data_get_api_response("endpoint", "auth_token", method="POST", payload={"key": "value"})

        assert response == {"type": "success", "data": "some_data"}
        mock_client.post.assert_called_once()
        mock_logger[1].info.assert_any_call("=== API Request Details ===")
        mock_logger[1].info.assert_any_call("=== API Response Details ===")

    def test_get_api_response_get_success(self, mock_httpx_client, mock_logger):
        mock_client = mock_httpx_client
        mock_client.get.return_value = MagicMock(status_code=200, json=lambda: {"type": "success", "data": "some_data"})

        response = data_get_api_response("endpoint", "auth_token", method="GET", params={"key": "value"})

        assert response == {"type": "success", "data": "some_data"}
        mock_client.get.assert_called_once()
        mock_logger[1].info.assert_any_call("=== API Request Details ===")
        mock_logger[1].info.assert_any_call("=== API Response Details ===")

    def test_get_api_response_post_api_error(self, mock_httpx_client, mock_logger):
        mock_client = mock_httpx_client
        mock_client.post.return_value = MagicMock(status_code=400, json=lambda: {"type": "error", "description": "Bad Request"})

        response = data_get_api_response("endpoint", "auth_token", method="POST", payload={"key": "value"})

        assert response == {"type": "error", "description": "Bad Request"}
        mock_client.post.assert_called_once()
        mock_logger[1].info.assert_any_call("=== API Request Details ===")
        mock_logger[1].info.assert_any_call("=== API Response Details ===")

    def test_get_api_response_exception(self, mock_httpx_client, mock_logger):
        mock_client = mock_httpx_client
        mock_client.post.side_effect = Exception("Network unreachable")

        with pytest.raises(Exception, match="Network unreachable"):
            data_get_api_response("endpoint", "auth_token", method="POST", payload={"key": "value"})

        mock_logger[1].error.assert_called_once_with("API request failed: Network unreachable")

    def test_get_api_response_invalid_payload_format(self, mock_httpx_client, mock_logger):
        mock_client = mock_httpx_client
        mock_client.post.return_value = MagicMock(status_code=200, json=lambda: {"type": "success"})

        with pytest.raises(Exception, match="Invalid payload format"):
            data_get_api_response("endpoint", "auth_token", method="POST", payload="not_json")

        mock_logger[1].error.assert_called_once_with("Failed to parse payload as JSON")

class TestBrokerData:
    @pytest.fixture(autouse=True)
    def setup(self, mock_db_session, mock_symtoken, mock_get_br_symbol, mock_logger):
        self.mock_db_session = mock_db_session
        self.mock_symtoken = mock_symtoken
        self.mock_get_br_symbol = mock_get_br_symbol
        self.mock_logger = mock_logger
        self.broker_data = BrokerData("test_auth_token", "test_feed_token", "test_user_id")

    def test_get_instrument_token_success(self):
        # Mock SymToken instance
        mock_symbol_info = MagicMock()
        mock_symbol_info.token = "12345"
        self.mock_db_session.query.return_value.filter.return_value.first.return_value = mock_symbol_info

        symbol_info, brexchange = self.broker_data._get_instrument_token("NIFTY", "NSE")

        self.mock_get_br_symbol.assert_called_once_with("NIFTY", "NSE")
        self.mock_db_session.query.assert_called_once_with(self.mock_symtoken)
        self.mock_db_session.query.return_value.filter.assert_called_once()
        assert symbol_info == mock_symbol_info
        assert brexchange == 1  # NSE maps to 1

    def test_get_instrument_token_unknown_exchange(self):
        with pytest.raises(Exception, match="Unknown exchange segment: UNKNOWN"):
            self.broker_data._get_instrument_token("NIFTY", "UNKNOWN")

        self.mock_get_br_symbol.assert_called_once_with("NIFTY", "UNKNOWN")
        self.mock_db_session.query.assert_not_called() # Should not query DB if exchange is unknown

    def test_get_instrument_token_symbol_not_found_in_db(self):
        self.mock_db_session.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(Exception, match="Could not find exchange token for NSE:IBULLS_SYMBOL"):
            self.broker_data._get_instrument_token("NIFTY", "NSE")

        self.mock_get_br_symbol.assert_called_once_with("NIFTY", "NSE")
        self.mock_db_session.query.assert_called_once_with(self.mock_symtoken)
        self.mock_db_session.query.return_value.filter.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.web.broker.broker.ibulls.api.data.data_get_api_response")
    async def test_fetch_market_data_success(self, mock_data_get_api_response):
        mock_data_get_api_response.return_value = {"type": "success", "result": [{"ltp": "100.00"}]}
        
        market_data = await self.broker_data._fetch_market_data("IBULLS_SYMBOL", "NSE", "feed_token_123")
        
        mock_data_get_api_response.assert_called_once_with(
            "market_data_endpoint",
            "feed_token_123",
            method="GET",
            params={"symbol": "IBULLS_SYMBOL", "exchange": "NSE"}
        )
        assert market_data == {"ltp": "100.00"}

    @pytest.mark.asyncio
    @patch("app.web.broker.broker.ibulls.api.data.data_get_api_response")
    async def test_fetch_market_data_api_error(self, mock_data_get_api_response):
        mock_data_get_api_response.return_value = {"type": "error", "description": "Market data error"}
        
        market_data = await self.broker_data._fetch_market_data("IBULLS_SYMBOL", "NSE", "feed_token_123")
        
        self.mock_logger[1].error.assert_called_once_with("Failed to fetch market data for IBULLS_SYMBOL on NSE: Market data error")
        assert market_data == {}
@pytest.mark.asyncio
@patch("app.web.broker.broker.ibulls.api.data.data_get_api_response")
async def test_fetch_market_data_exception(self, mock_data_get_api_response):
    mock_data_get_api_response.side_effect = Exception("Connection error")
    
    market_data = await self.broker_data._fetch_market_data("IBULLS_SYMBOL", "NSE", "feed_token_123")
    
    self.mock_logger[1].error.assert_called_once_with("Error in _fetch_market_data (code 1502): Connection error", exc_info=True)
    assert market_data is None


@pytest.mark.asyncio
@patch('app.web.broker.broker.ibulls.api.data.BrokerData._get_instrument_token')
@patch('app.web.broker.broker.ibulls.api.data.BrokerData._fetch_market_data')
async def test_get_quotes_success_with_oi(self, mock_fetch_market_data, mock_get_instrument_token):
    mock_get_instrument_token.return_value = (MagicMock(token="TOKEN123"), 1) # (symbol_info, brexchange)
    mock_fetch_market_data.side_effect = [
        {"Touchline": {"AskInfo": {"Price": 101.0}, "BidInfo": {"Price": 100.0}, "High": 105.0, "Low": 99.0, "LastTradedPrice": 100.5, "Open": 100.0, "Close": 99.5, "TotalTradedQuantity": 1000}}, # Market data
        {"OpenInterest": 5000} # OI data
    ]

    quotes = await self.broker_data.get_quotes("SYMBOL", "NSE")

    mock_get_instrument_token.assert_called_once_with("SYMBOL", "NSE")
    assert mock_fetch_market_data.call_count == 2
    mock_fetch_market_data.assert_any_call({'exchangeSegment': 1, 'exchangeInstrumentID': 'TOKEN123'}, 1502)
    mock_fetch_market_data.assert_any_call({'exchangeSegment': 1, 'exchangeInstrumentID': 'TOKEN123'}, 1510)
    assert quotes == {
        'ask': 101.0, 'bid': 100.0, 'high': 105.0, 'low': 99.0,
        'ltp': 100.5, 'open': 100.0, 'prev_close': 99.5,
        'volume': 1000, 'oi': 5000
    }

@pytest.mark.asyncio
@patch('app.web.broker.broker.ibulls.api.data.BrokerData._get_instrument_token')
@patch('app.web.broker.broker.ibulls.api.data.BrokerData._fetch_market_data')
async def test_get_quotes_success_no_oi(self, mock_fetch_market_data, mock_get_instrument_token):
    mock_get_instrument_token.return_value = (MagicMock(token="TOKEN123"), 1)
    mock_fetch_market_data.side_effect = [
        {"Touchline": {"AskInfo": {"Price": 101.0}, "BidInfo": {"Price": 100.0}, "High": 105.0, "Low": 99.0, "LastTradedPrice": 100.5, "Open": 100.0, "Close": 99.5, "TotalTradedQuantity": 1000}}, # Market data
        None # No OI data
    ]

    quotes = await self.broker_data.get_quotes("SYMBOL", "NSE")

    assert quotes['oi'] == 0
    self.mock_logger[1].warning.assert_called_with("Failed to fetch OI data: Failed to fetch market data")

@pytest.mark.asyncio
@patch('app.web.broker.broker.ibulls.api.data.BrokerData._get_instrument_token')
@patch('app.web.broker.broker.ibulls.api.data.BrokerData._fetch_market_data')
async def test_get_quotes_fetch_market_data_fails(self, mock_fetch_market_data, mock_get_instrument_token):
    mock_get_instrument_token.return_value = (MagicMock(token="TOKEN123"), 1)
    mock_fetch_market_data.return_value = None # Market data fetch fails

    with pytest.raises(Exception, match="Failed to fetch market data"):
        await self.broker_data.get_quotes("SYMBOL", "NSE")
    
    self.mock_logger[1].error.assert_called_once_with("Error fetching quotes: Failed to fetch market data")

@pytest.mark.asyncio
@patch('app.web.broker.broker.ibulls.api.data.BrokerData._get_instrument_token')
async def test_get_quotes_get_instrument_token_fails(self, mock_get_instrument_token):
    mock_get_instrument_token.side_effect = Exception("Token not found")

    with pytest.raises(Exception, match="Error fetching quotes: Token not found"):
        await self.broker_data.get_quotes("SYMBOL", "NSE")
    
    self.mock_logger[1].error.assert_called_once_with("Error fetching quotes: Token not found")

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.ibulls.api.data.BrokerData._get_instrument_token')
    @patch('app.web.broker.broker.ibulls.api.data.BrokerData._fetch_market_data')
    async def test_get_market_depth_success(self, mock_fetch_market_data, mock_get_instrument_token):
        mock_get_instrument_token.return_value = (MagicMock(token="TOKEN123"), 1)
        mock_fetch_market_data.return_value = {
            "TotalBuyQty": 1000,
            "TotalSellQty": 800,
            "Depth": [
                {"BuyQty": 100, "BuyPrice": 99.5, "SellQty": 50, "SellPrice": 100.5},
                {"BuyQty": 200, "BuyPrice": 99.0, "SellQty": 100, "SellPrice": 101.0},
            ]
        }

        depth_data = await self.broker_data.get_market_depth("SYMBOL", "NSE")

        mock_get_instrument_token.assert_called_once_with("SYMBOL", "NSE")
        mock_fetch_market_data.assert_called_once_with({'exchangeSegment': 1, 'exchangeInstrumentID': 'TOKEN123'}, 1502)
        assert depth_data == {
            'total_buy_qty': 1000,
            'total_sell_qty': 800,
            'depth': [
                {'buy_qty': 100, 'buy_price': 99.5, 'sell_qty': 50, 'sell_price': 100.5},
                {'buy_qty': 200, 'buy_price': 99.0, 'sell_qty': 100, 'sell_price': 101.0},
            ]
        }

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.ibulls.api.data.BrokerData._get_instrument_token')
    @patch('app.web.broker.broker.ibulls.api.data.BrokerData._fetch_market_data')
    async def test_get_market_depth_fetch_market_data_fails(self, mock_fetch_market_data, mock_get_instrument_token):
        mock_get_instrument_token.return_value = (MagicMock(token="TOKEN123"), 1)
        mock_fetch_market_data.return_value = None

        depth_data = await self.broker_data.get_market_depth("SYMBOL", "NSE")

        self.mock_logger[1].error.assert_called_once_with("Error fetching market depth: Failed to fetch market data")
        assert depth_data is None

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.ibulls.api.data.BrokerData._get_instrument_token')
    async def test_get_market_depth_get_instrument_token_fails(self, mock_get_instrument_token):
        mock_get_instrument_token.side_effect = Exception("Token not found")

        depth_data = await self.broker_data.get_market_depth("SYMBOL", "NSE")

        self.mock_logger[1].error.assert_called_once_with("Error fetching market depth: Token not found")
        assert depth_data is None

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.ibulls.api.data.BrokerData._get_instrument_token')
    @patch('app.web.broker.broker.ibulls.api.data.BrokerData._fetch_market_data')
    async def test_get_depth_success(self, mock_fetch_market_data, mock_get_instrument_token):
        mock_get_instrument_token.return_value = (MagicMock(token="TOKEN123"), 1)
        mock_fetch_market_data.return_value = {
            "TotalBuyQty": 1000,
            "TotalSellQty": 800,
            "Depth": [
                {"BuyQty": 100, "BuyPrice": 99.5, "SellQty": 50, "SellPrice": 100.5},
                {"BuyQty": 200, "BuyPrice": 99.0, "SellQty": 100, "SellPrice": 101.0},
            ]
        }

        depth_data = await self.broker_data.get_depth("SYMBOL", "NSE")

        mock_get_instrument_token.assert_called_once_with("SYMBOL", "NSE")
        mock_fetch_market_data.assert_called_once_with({'exchangeSegment': 1, 'exchangeInstrumentID': 'TOKEN123'}, 1502)
        assert depth_data == {
            'total_buy_qty': 1000,
            'total_sell_qty': 800,
            'depth': [
                {'buy_qty': 100, 'buy_price': 99.5, 'sell_qty': 50, 'sell_price': 100.5},
                {'buy_qty': 200, 'buy_price': 99.0, 'sell_qty': 100, 'sell_price': 101.0},
            ]
        }

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.ibulls.api.data.BrokerData._get_instrument_token')
    @patch('app.web.broker.broker.ibulls.api.data.BrokerData._fetch_market_data')
    async def test_get_depth_fetch_market_data_fails(self, mock_fetch_market_data, mock_get_instrument_token):
        mock_get_instrument_token.return_value = (MagicMock(token="TOKEN123"), 1)
        mock_fetch_market_data.return_value = None

        depth_data = await self.broker_data.get_depth("SYMBOL", "NSE")

        self.mock_logger[1].error.assert_called_once_with("Error fetching depth: Failed to fetch market data")
        assert depth_data is None

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.ibulls.api.data.BrokerData._get_instrument_token')
    async def test_get_depth_get_instrument_token_fails(self, mock_get_instrument_token):
        mock_get_instrument_token.side_effect = Exception("Token not found")

        depth_data = await self.broker_data.get_depth("SYMBOL", "NSE")

        self.mock_logger[1].error.assert_called_once_with("Error fetching depth: Token not found")
        assert depth_data is None


# --- Data API Tests ---

class TestHistoryAPI:
    @pytest.fixture(autouse=True)
    def setup(self, mock_settings, mock_httpx_client, mock_logger, mock_db_session, mock_symtoken, mock_get_br_symbol):
        self.auth_token = "test_auth_token"
        self.feed_token = "test_feed_token"
        self.user_id = "test_user_id"
        self.broker_data = BrokerData(self.auth_token, self.feed_token, self.user_id)
        self.mock_logger = mock_logger
        self.mock_db_session = mock_db_session
        self.mock_symtoken = mock_symtoken
        self.mock_get_br_symbol = mock_get_br_symbol

    @pytest.mark.asyncio
    @patch('app.core.schemas.token_db.get_br_symbol', return_value="BRSYMBOL")
    @patch('app.web.broker.broker.ibulls.api.data.db_session')
    @patch('app.web.broker.broker.ibulls.api.data.data_get_api_response')
    async def test_get_history_success_1m(self, mock_data_get_api_response, mock_db_session_context, mock_get_br_symbol_func):
        mock_db_session_context.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = MagicMock(token="TOKEN123")
        mock_data_get_api_response.return_value = {
            "type": "success",
            "result": {
                "dataReponse": "1700000000|100.0|101.0|99.0|100.5|1000,1700000060|100.5|101.5|99.5|101.0|1200"
            }
        }

        from_date = "2023-11-15"
        to_date = "2023-11-15"
        df = await self.broker_data.get_history("SYMBOL", "NSE", "1m", from_date, to_date)

        mock_get_br_symbol_func.assert_called_once_with("SYMBOL", "NSE")
        mock_db_session_context.return_value.__enter__.return_value.query.return_value.filter.assert_called_once()
        mock_data_get_api_response.assert_called_once()

        assert not df.empty
        assert len(df) == 2
        assert df['open'].iloc[0] == 100.0
        assert df['close'].iloc[1] == 101.0

    @pytest.mark.asyncio
    @patch('app.core.schemas.token_db.get_br_symbol', side_effect=Exception("Symbol error"))
    async def test_get_history_get_br_symbol_fails(self, mock_get_br_symbol_func):
        from_date = "2023-11-15"
        to_date = "2023-11-15"
        with pytest.raises(Exception, match="Error getting history: Symbol error"):
            await self.broker_data.get_history("SYMBOL", "NSE", "1m", from_date, to_date)
        mock_get_br_symbol_func.assert_called_once_with("SYMBOL", "NSE")
        self.mock_logger[1].error.assert_called_once_with("Error getting history: Symbol error")

    @pytest.mark.asyncio
    @patch('app.core.schemas.token_db.get_br_symbol', return_value="BRSYMBOL")
    @patch('app.web.broker.broker.ibulls.api.data.db_session')
    @patch('app.web.broker.broker.ibulls.api.data.data_get_api_response')
    async def test_get_history_instrument_token_not_found(self, mock_data_get_api_response, mock_db_session_context, mock_get_br_symbol_func):
        mock_db_session_context.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None

        from_date = "2023-11-15"
        to_date = "2023-11-15"
        with pytest.raises(Exception, match="Error getting history: Could not find exchange token for NSE:BRSYMBOL"):
            await self.broker_data.get_history("SYMBOL", "NSE", "1m", from_date, to_date)
        mock_get_br_symbol_func.assert_called_once_with("SYMBOL", "NSE")
        mock_db_session_context.return_value.__enter__.return_value.query.return_value.filter.assert_called_once()
        mock_data_get_api_response.assert_not_called()
        self.mock_logger[1].error.assert_called_once_with("Error getting history: Could not find exchange token for NSE:BRSYMBOL")

    @pytest.mark.asyncio
    @patch('app.core.schemas.token_db.get_br_symbol', return_value="BRSYMBOL")
    @patch('app.web.broker.broker.ibulls.api.data.db_session')
    @patch('app.web.broker.broker.ibulls.api.data.data_get_api_response')
    async def test_get_history_api_error(self, mock_data_get_api_response, mock_db_session_context, mock_get_br_symbol_func):
        mock_db_session_context.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = MagicMock(token="TOKEN123")
        mock_data_get_api_response.return_value = {"type": "error", "description": "API error"}

        from_date = "2023-11-15"
        to_date = "2023-11-15"
        with pytest.raises(Exception, match="Error getting history: API error"):
            await self.broker_data.get_history("SYMBOL", "NSE", "1m", from_date, to_date)
        mock_get_br_symbol_func.assert_called_once_with("SYMBOL", "NSE")
        mock_db_session_context.return_value.__enter__.return_value.query.return_value.filter.assert_called_once()
        mock_data_get_api_response.assert_called_once()
        self.mock_logger[1].error.assert_called_once_with("Error getting history: API error")

    @pytest.mark.asyncio
    @patch('app.core.schemas.token_db.get_br_symbol', return_value="BRSYMBOL")
    @patch('app.web.broker.broker.ibulls.api.data.db_session')
    @patch('app.web.broker.broker.ibulls.api.data.data_get_api_response', side_effect=Exception("Connection error"))
    async def test_get_history_exception_during_api_call(self, mock_data_get_api_response, mock_db_session_context, mock_get_br_symbol_func):
        mock_db_session_context.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = MagicMock(token="TOKEN123")

        from_date = "2023-11-15"
        to_date = "2023-11-15"
        with pytest.raises(Exception, match="Error getting history: Connection error"):
            await self.broker_data.get_history("SYMBOL", "NSE", "1m", from_date, to_date)
        mock_get_br_symbol_func.assert_called_once_with("SYMBOL", "NSE")
        mock_db_session_context.return_value.__enter__.return_value.query.return_value.filter.assert_called_once()
        mock_data_get_api_response.assert_called_once()
        self.mock_logger[1].error.assert_called_once_with("Error getting history: Connection error", exc_info=True)

    @pytest.mark.asyncio
    @patch('app.core.schemas.token_db.get_br_symbol', return_value="BRSYMBOL")
    @patch('app.web.broker.broker.ibulls.api.data.db_session')
    @patch('app.web.broker.broker.ibulls.api.data.data_get_api_response')
    async def test_get_history_no_data_response(self, mock_data_get_api_response, mock_db_session_context, mock_get_br_symbol_func):
        mock_db_session_context.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = MagicMock(token="TOKEN123")
        mock_data_get_api_response.return_value = {"type": "success", "result": {}}

        from_date = "2023-11-15"
        to_date = "2023-11-15"
        df = await self.broker_data.get_history("SYMBOL", "NSE", "1m", from_date, to_date)
        
        assert df.empty
        self.mock_logger[1].warning.assert_called_once_with("No dataReponse in history API response for SYMBOL on NSE")

    @pytest.mark.asyncio
    @patch('app.core.schemas.token_db.get_br_symbol', return_value="BRSYMBOL")
    @patch('app.web.broker.broker.ibulls.api.data.db_session')
    @patch('app.web.broker.broker.ibulls.api.data.data_get_api_response')
    async def test_get_history_empty_data_response(self, mock_data_get_api_response, mock_db_session_context, mock_get_br_symbol_func):
        mock_db_session_context.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = MagicMock(token="TOKEN123")
        mock_data_get_api_response.return_value = {"type": "success", "result": {"dataReponse": ""}}

        from_date = "2023-11-15"
        to_date = "2023-11-15"
        df = await self.broker_data.get_history("SYMBOL", "NSE", "1m", from_date, to_date)
        
        assert df.empty
        self.mock_logger[1].warning.assert_called_once_with("Empty dataReponse in history API response for SYMBOL on NSE")



class TestOrderBook:
    @pytest.fixture(autouse=True)
    def setup(self, mock_logger):
        self.mock_logger = mock_logger[2] # Use the order_api logger

    @patch("app.web.broker.broker.ibulls.api.order_api.get_api_response")
    def test_get_order_book_success(self, mock_order_get_api_response):
        mock_order_get_api_response.return_value = {
            "type": "success",
            "result": [
                {"AppOrderID": "1", "OrderStatus": "New"},
                {"AppOrderID": "2", "OrderStatus": "Filled"}
            ]
        }
        auth_token = "test_auth_token"
        response = get_order_book(auth_token)

        mock_order_get_api_response.assert_called_once_with("/orders", auth_token)
        assert response == {
            "type": "success",
            "result": [
                {"AppOrderID": "1", "OrderStatus": "New"},
                {"AppOrderID": "2", "OrderStatus": "Filled"}
            ]
        }
        self.mock_logger.info.assert_called_with("Order book response: {'type': 'success', 'result': [{'AppOrderID': '1', 'OrderStatus': 'New'}, {'AppOrderID': '2', 'OrderStatus': 'Filled'}]}")

    @patch("app.web.broker.broker.ibulls.api.order_api.get_api_response")
    def test_get_order_book_api_error(self, mock_order_get_api_response):
        mock_order_get_api_response.return_value = {
            "type": "error",
            "message": "Failed to retrieve order book"
        }
        auth_token = "test_auth_token"
        response = get_order_book(auth_token)

        mock_order_get_api_response.assert_called_once_with("/orders", auth_token)
        assert response == {
            "type": "error",
            "message": "Failed to retrieve order book"
class TestTradeBook:
    @pytest.fixture(autouse=True)
    def setup(self, mock_logger):
        self.mock_logger = mock_logger[2]  # Use the order_api logger

    @patch("app.web.broker.broker.ibulls.api.order_api.get_api_response")
    def test_get_trade_book_success(self, mock_order_get_api_response):
        mock_order_get_api_response.return_value = {
            "type": "success",
            "result": [
                {"TradeID": "T1", "Symbol": "AAPL"},
                {"TradeID": "T2", "Symbol": "GOOGL"}
            ]
        }
        auth_token = "test_auth_token"
        response = get_trade_book(auth_token)

        mock_order_get_api_response.assert_called_once_with("/orders/trades", auth_token)
        assert response == {
            "type": "success",
            "result": [
                {"TradeID": "T1", "Symbol": "AAPL"},
                {"TradeID": "T2", "Symbol": "GOOGL"}
            ]
        }
        self.mock_logger.info.assert_called_with("Trade book response: {'type': 'success', 'result': [{'TradeID': 'T1', 'Symbol': 'AAPL'}, {'TradeID': 'T2', 'Symbol': 'GOOGL'}]}")

    @patch("app.web.broker.broker.ibulls.api.order_api.get_api_response")
    def test_get_trade_book_api_error(self, mock_order_get_api_response):
        mock_order_get_api_response.return_value = {
            "type": "error",
            "message": "Failed to retrieve trade book"
        }
        auth_token = "test_auth_token"
        response = get_trade_book(auth_token)

        mock_order_get_api_response.assert_called_once_with("/orders/trades", auth_token)
        assert response == {
            "type": "error",
            "message": "Failed to retrieve trade book"
        }
        self.mock_logger.info.assert_called_with("Trade book response: {'type': 'error', 'message': 'Failed to retrieve trade book'}")

    @patch("app.web.broker.broker.ibulls.api.order_api.get_api_response", side_effect=Exception("Network error"))
    def test_get_trade_book_exception(self, mock_order_get_api_response):
        auth_token = "test_auth_token"
        response = get_trade_book(auth_token)

        mock_order_get_api_response.assert_called_once_with("/orders/trades", auth_token)
        assert response == {"status": "error", "message": "Error fetching trade book: Network error"}
        self.mock_logger.exception.assert_called_once_with("Error fetching trade book: Network error")
class TestPositions:
    @pytest.fixture(autouse=True)
    def setup(self, mock_logger):
        self.mock_logger = mock_logger[2]  # Use the order_api logger

    @patch("app.web.broker.broker.ibulls.api.order_api.get_api_response")
    def test_get_positions_success(self, mock_order_get_api_response):
        mock_order_get_api_response.return_value = {
            "type": "success",
            "result": {
                "positionList": [
                    {"TradingSymbol": "AAPL", "Quantity": "10", "ProductType": "CNC"},
                    {"TradingSymbol": "GOOGL", "Quantity": "-5", "ProductType": "MIS"}
                ]
            }
        }
        auth_token = "test_auth_token"
        response = get_positions(auth_token)

        mock_order_get_api_response.assert_called_once_with("/portfolio/positions?dayOrNet=NetWise", auth_token)
        assert response == {
            "type": "success",
            "result": {
                "positionList": [
                    {"TradingSymbol": "AAPL", "Quantity": "10", "ProductType": "CNC"},
                    {"TradingSymbol": "GOOGL", "Quantity": "-5", "ProductType": "MIS"}
                ]
            }
        }
        self.mock_logger.info.assert_called_with("Positions response: {'type': 'success', 'result': {'positionList': [{'TradingSymbol': 'AAPL', 'Quantity': '10', 'ProductType': 'CNC'}, {'TradingSymbol': 'GOOGL', 'Quantity': '-5', 'ProductType': 'MIS'}]}}")

    @patch("app.web.broker.broker.ibulls.api.order_api.get_api_response")
    def test_get_positions_api_error(self, mock_order_get_api_response):
        mock_order_get_api_response.return_value = {
            "type": "error",
            "message": "Failed to retrieve positions"
        }
        auth_token = "test_auth_token"
        response = get_positions(auth_token)

        mock_order_get_api_response.assert_called_once_with("/portfolio/positions?dayOrNet=NetWise", auth_token)
        assert response == {
            "type": "error",
            "message": "Failed to retrieve positions"
        }
        self.mock_logger.info.assert_called_with("Positions response: {'type': 'error', 'message': 'Failed to retrieve positions'}")

    @patch("app.web.broker.broker.ibulls.api.order_api.get_api_response", side_effect=Exception("Network error"))
    def test_get_positions_exception(self, mock_order_get_api_response):
        auth_token = "test_auth_token"
        response = get_positions(auth_token)

        mock_order_get_api_response.assert_called_once_with("/portfolio/positions?dayOrNet=NetWise", auth_token)
        assert response == {"status": "error", "message": "Error fetching positions: Network error"}
        self.mock_logger.exception.assert_called_once_with("Error fetching positions: Network error")


class TestHoldings:
    @pytest.fixture(autouse=True)
    def setup(self, mock_logger):
        self.mock_logger = mock_logger[2]  # Use the order_api logger

    @patch("app.web.broker.broker.ibulls.api.order_api.get_api_response")
    def test_get_holdings_success(self, mock_order_get_api_response):
        mock_order_get_api_response.return_value = {
            "type": "success",
            "result": {
                "holdingList": [
                    {"EQSymbol": "RELIANCE", "Quantity": "50"},
                    {"EQSymbol": "TCS", "Quantity": "20"}
                ]
            }
        }
        auth_token = "test_auth_token"
        response = get_holdings(auth_token)

        mock_order_get_api_response.assert_called_once_with("/portfolio/holdings", auth_token)
        assert response == {
            "type": "success",
            "result": {
                "holdingList": [
                    {"EQSymbol": "RELIANCE", "Quantity": "50"},
                    {"EQSymbol": "TCS", "Quantity": "20"}
                ]
            }
        }
        self.mock_logger.info.assert_called_with("Holdings response: {'type': 'success', 'result': {'holdingList': [{'EQSymbol': 'RELIANCE', 'Quantity': '50'}, {'EQSymbol': 'TCS', 'Quantity': '20'}]}}")

    @patch("app.web.broker.broker.ibulls.api.order_api.get_api_response")
    def test_get_holdings_api_error(self, mock_order_get_api_response):
        mock_order_get_api_response.return_value = {
            "type": "error",
            "message": "Failed to retrieve holdings"
        }
        auth_token = "test_auth_token"
        response = get_holdings(auth_token)

        mock_order_get_api_response.assert_called_once_with("/portfolio/holdings", auth_token)
        assert response == {
            "type": "error",
            "message": "Failed to retrieve holdings"
        }
        self.mock_logger.info.assert_called_with("Holdings response: {'type': 'error', 'message': 'Failed to retrieve holdings'}")

    @patch("app.web.broker.broker.ibulls.api.order_api.get_api_response", side_effect=Exception("Network error"))
    def test_get_holdings_exception(self, mock_order_get_api_response):
        auth_token = "test_auth_token"
        response = get_holdings(auth_token)

        mock_order_get_api_response.assert_called_once_with("/portfolio/holdings", auth_token)
        assert response == {"status": "error", "message": "Error fetching holdings: Network error"}
        self.mock_logger.exception.assert_called_once_with("Error fetching holdings: Network error")


class TestOrderBook:
    @pytest.fixture(autouse=True)
    def setup(self, mock_logger):
        self.mock_logger = mock_logger[2] # Use the order_api logger

    @patch("app.web.broker.broker.ibulls.api.order_api.get_api_response")
    def test_get_order_book_success(self, mock_order_get_api_response):
        mock_order_get_api_response.return_value = {
            "type": "success",
            "result": [
                {"AppOrderID": "1", "OrderStatus": "New"},
                {"AppOrderID": "2", "OrderStatus": "Filled"}
            ]
        }
        auth_token = "test_auth_token"
        response = get_order_book(auth_token)

        mock_order_get_api_response.assert_called_once_with("/orders", auth_token)
        assert response == {
            "type": "success",
            "result": [
                {"AppOrderID": "1", "OrderStatus": "New"},
                {"AppOrderID": "2", "OrderStatus": "Filled"}
            ]
        }
        self.mock_logger.info.assert_called_with("Order book response: {'type': 'success', 'result': [{'AppOrderID': '1', 'OrderStatus': 'New'}, {'AppOrderID': '2', 'OrderStatus': 'Filled'}]}")

    @patch("app.web.broker.broker.ibulls.api.order_api.get_api_response")
    def test_get_order_book_api_error(self, mock_order_get_api_response):
        mock_order_get_api_response.return_value = {
            "type": "error",
            "message": "Failed to retrieve order book"
        }
        auth_token = "test_auth_token"
        response = get_order_book(auth_token)

        mock_order_get_api_response.assert_called_once_with("/orders", auth_token)
        assert response == {
            "type": "error",
            "message": "Failed to retrieve order book"
        }
        self.mock_logger.info.assert_called_with("Order book response: {'type': 'error', 'message': 'Failed to retrieve order book'}")

    @patch("app.web.broker.broker.ibulls.api.order_api.get_api_response", side_effect=Exception("Network error"))
    def test_get_order_book_exception(self, mock_order_get_api_response):
        auth_token = "test_auth_token"
        response = get_order_book(auth_token)

        mock_order_get_api_response.assert_called_once_with("/orders", auth_token)
        assert response == {"status": "error", "message": "Error fetching order book: Network error"}
        self.mock_logger.exception.assert_called_once_with("Error fetching order book: Network error")


class TestOpenPosition:
    @pytest.fixture(autouse=True)
    def setup(self, mock_logger):
        self.mock_logger = mock_logger[2]  # Use the order_api logger

    @patch("app.web.broker.broker.ibulls.api.order_api.get_api_response")
    def test_get_open_position_success(self, mock_order_get_api_response):
        mock_order_get_api_response.return_value = {
            "type": "success",
            "result": {
                "openPositionList": [
                    {"TradingSymbol": "AAPL", "Quantity": "10", "ProductType": "CNC"},
                    {"TradingSymbol": "GOOGL", "Quantity": "-5", "ProductType": "MIS"}
                ]
            }
        }
        auth_token = "test_auth_token"
        response = get_open_position(auth_token)

        mock_order_get_api_response.assert_called_once_with("/portfolio/openposition", auth_token)
        assert response == {
            "type": "success",
            "result": {
                "openPositionList": [
                    {"TradingSymbol": "AAPL", "Quantity": "10", "ProductType": "CNC"},
                    {"TradingSymbol": "GOOGL", "Quantity": "-5", "ProductType": "MIS"}
                ]
            }
        }
        self.mock_logger.info.assert_called_with("Open position response: {'type': 'success', 'result': {'openPositionList': [{'TradingSymbol': 'AAPL', 'Quantity': '10', 'ProductType': 'CNC'}, {'TradingSymbol': 'GOOGL', 'Quantity': '-5', 'ProductType': 'MIS'}]}}")

    @patch("app.web.broker.broker.ibulls.api.order_api.get_api_response")
    def test_get_open_position_api_error(self, mock_order_get_api_response):
        mock_order_get_api_response.return_value = {
            "type": "error",
            "message": "Failed to retrieve open positions"
        }
        auth_token = "test_auth_token"
        response = get_open_position(auth_token)

        mock_order_get_api_response.assert_called_once_with("/portfolio/openposition", auth_token)

class TestPlaceOrderAPI:
    @pytest.fixture(autouse=True)
    def setup(self, mock_logger, mock_get_token):
        self.mock_logger = mock_logger[2]  # Use the order_api logger
        self.mock_get_token = mock_get_token

    @patch("app.web.broker.broker.ibulls.api.order_api.order_get_api_response")
    @patch("app.web.broker.broker.ibulls.api.order_api.get_br_symbol")
    def test_place_order_api_success(self, mock_get_br_symbol, mock_order_get_api_response):
        mock_get_br_symbol.return_value = "IBULLS_SYMBOL"
        mock_order_get_api_response.return_value = {
            "type": "success",
            "result": {"AppOrderID": "12345", "OrderNo": "67890"}
        }
        order_payload = {
            "tradingsymbol": "SYMBOL",
            "exchange": "NSE",
            "transaction_type": "BUY",
            "quantity": 1,
            "product_type": "CNC",
            "order_type": "MARKET",
            "price": 0,
        }
        auth_token = "test_auth_token"

        response = place_order_api(order_payload, auth_token)

        mock_get_br_symbol.assert_called_once_with("SYMBOL", "NSE")
        self.mock_get_token.assert_called_once_with("NSE", "IBULLS_SYMBOL")
        mock_order_get_api_response.assert_called_once() # Detailed payload assertion below
        
        # Verify the payload sent to the API
        called_payload = mock_order_get_api_response.call_args[1]['payload']
        assert called_payload["AppOrderID"] is not None
        assert called_payload["OrderNo"] is not None
        assert called_payload["TradingSymbol"] == "IBULLS_SYMBOL"
        assert called_payload["ExchangeSegment"] == 1 # NSE maps to 1
        assert called_payload["TransactionType"] == "BUY"
        assert called_payload["Quantity"] == 1
        assert called_payload["ProductType"] == "CNC"
        assert called_payload["OrderType"] == "MARKET"
        assert called_payload["Price"] == 0
        assert called_payload["InstrumentToken"] == "12345"

        assert response == {"AppOrderID": "12345", "OrderNo": "67890", "status": "success"}
        self.mock_logger.info.assert_called_with(f"Order placed successfully: AppOrderID=12345, OrderNo=67890")

    @patch("app.web.broker.broker.ibulls.api.order_api.order_get_api_response")
    @patch("app.web.broker.broker.ibulls.api.order_api.get_br_symbol")
    def test_place_order_api_api_error(self, mock_get_br_symbol, mock_order_get_api_response):
        mock_get_br_symbol.return_value = "IBULLS_SYMBOL"
        mock_order_get_api_response.return_value = {
            "type": "error",
            "message": "Order placement failed"
        }
        order_payload = {
            "tradingsymbol": "SYMBOL",
            "exchange": "NSE",
            "transaction_type": "BUY",
            "quantity": 1,
            "product_type": "CNC",
            "order_type": "MARKET",
            "price": 0,
        }
        auth_token = "test_auth_token"

        response = place_order_api(order_payload, auth_token)

        mock_get_br_symbol.assert_called_once_with("SYMBOL", "NSE")
        self.mock_get_token.assert_called_once_with("NSE", "IBULLS_SYMBOL")
        mock_order_get_api_response.assert_called_once()

        assert response == {"status": "error", "message": "Order placement failed"}
        self.mock_logger.error.assert_called_with("Order placement failed: Order placement failed")

    @patch("app.web.broker.broker.ibulls.api.order_api.order_get_api_response", side_effect=Exception("Network error"))
    @patch("app.web.broker.broker.ibulls.api.order_api.get_br_symbol")
    def test_place_order_api_exception(self, mock_get_br_symbol, mock_order_get_api_response):
        mock_get_br_symbol.return_value = "IBULLS_SYMBOL"
        order_payload = {
            "tradingsymbol": "SYMBOL",
            "exchange": "NSE",
            "transaction_type": "BUY",
            "quantity": 1,
            "product_type": "CNC",
            "order_type": "MARKET",
            "price": 0,
        }
        auth_token = "test_auth_token"

        response = place_order_api(order_payload, auth_token)

        mock_get_br_symbol.assert_called_once_with("SYMBOL", "NSE")
        self.mock_get_token.assert_called_once_with("NSE", "IBULLS_SYMBOL")
        mock_order_get_api_response.assert_called_once()

        assert response == {"status": "error", "message": "Error placing order: Network error"}
        self.mock_logger.exception.assert_called_once_with("Error placing order: Network error")

    @patch("app.web.broker.broker.ibulls.api.order_api.get_br_symbol", side_effect=Exception("Symbol lookup error"))
    def test_place_order_api_symbol_lookup_error(self, mock_get_br_symbol):
        order_payload = {
            "tradingsymbol": "SYMBOL",
            "exchange": "NSE",
            "transaction_type": "BUY",
            "quantity": 1,
            "product_type": "CNC",
            "order_type": "MARKET",
            "price": 0,
        }
        auth_token = "test_auth_token"

        response = place_order_api(order_payload, auth_token)

        mock_get_br_symbol.assert_called_once_with("SYMBOL", "NSE")
        assert response == {"status": "error", "message": "Symbol lookup error"}
        self.mock_logger.exception.assert_called_once_with("Error placing order: Symbol lookup error")
        assert response == {
            "type": "error",
            "message": "Failed to retrieve open positions"
        }
        self.mock_logger.info.assert_called_with("Open position response: {'type': 'error', 'message': 'Failed to retrieve open positions'}")

class TestPlaceSmartOrderAPI:
    @pytest.fixture(autouse=True)
    def setup(self, mock_logger, mock_get_token):
        self.mock_logger = mock_logger[2]  # Use the order_api logger
        self.mock_get_token = mock_get_token

    @patch("app.web.broker.broker.ibulls.api.order_api.order_get_api_response")
    @patch("app.web.broker.broker.ibulls.api.order_api.get_br_symbol")
    def test_place_smartorder_api_success(self, mock_get_br_symbol, mock_order_get_api_response):
        mock_get_br_symbol.return_value = "IBULLS_SYMBOL"
        mock_order_get_api_response.return_value = {
            "type": "success",
            "result": {"AppOrderID": "12345", "OrderNo": "67890"}
        }
        order_payload = {
            "tradingsymbol": "SYMBOL",
            "exchange": "NSE",
            "transaction_type": "BUY",
            "quantity": 1,
            "product_type": "CNC",
            "order_type": "MARKET",
            "price": 0,
        }
        auth_token = "test_auth_token"

        response = place_smartorder_api(order_payload, auth_token)

        mock_get_br_symbol.assert_called_once_with("SYMBOL", "NSE")
        self.mock_get_token.assert_called_once_with("NSE", "IBULLS_SYMBOL")
        mock_order_get_api_response.assert_called_once()
        
        # Verify the payload sent to the API
        called_payload = mock_order_get_api_response.call_args[1]['payload']
        assert called_payload["AppOrderID"] is not None
        assert called_payload["OrderNo"] is not None
        assert called_payload["TradingSymbol"] == "IBULLS_SYMBOL"
        assert called_payload["ExchangeSegment"] == 1 # NSE maps to 1
        assert called_payload["TransactionType"] == "BUY"
        assert called_payload["Quantity"] == 1
        assert called_payload["ProductType"] == "CNC"
        assert called_payload["OrderType"] == "MARKET"
        assert called_payload["Price"] == 0
        assert called_payload["InstrumentToken"] == "12345"

        assert response == {"AppOrderID": "12345", "OrderNo": "67890", "status": "success"}
        self.mock_logger.info.assert_called_with(f"Smart order placed successfully: AppOrderID=12345, OrderNo=67890")

    @patch("app.web.broker.broker.ibulls.api.order_api.order_get_api_response")
    @patch("app.web.broker.broker.ibulls.api.order_api.get_br_symbol")
    def test_place_smartorder_api_api_error(self, mock_get_br_symbol, mock_order_get_api_response):
        mock_get_br_symbol.return_value = "IBULLS_SYMBOL"
        mock_order_get_api_response.return_value = {
            "type": "error",
            "message": "Smart order placement failed"
        }
        order_payload = {
            "tradingsymbol": "SYMBOL",
            "exchange": "NSE",
            "transaction_type": "BUY",
            "quantity": 1,
            "product_type": "CNC",
            "order_type": "MARKET",
            "price": 0,
        }
        auth_token = "test_auth_token"

        response = place_smartorder_api(order_payload, auth_token)

        mock_get_br_symbol.assert_called_once_with("SYMBOL", "NSE")
        self.mock_get_token.assert_called_once_with("NSE", "IBULLS_SYMBOL")
        mock_order_get_api_response.assert_called_once()

        assert response == {"status": "error", "message": "Smart order placement failed"}
        self.mock_logger.error.assert_called_with("Smart order placement failed: Smart order placement failed")

    @patch("app.web.broker.broker.ibulls.api.order_api.order_get_api_response", side_effect=Exception("Network error"))
    @patch("app.web.broker.broker.ibulls.api.order_api.get_br_symbol")
    def test_place_smartorder_api_exception(self, mock_get_br_symbol, mock_order_get_api_response):
        mock_get_br_symbol.return_value = "IBULLS_SYMBOL"
        order_payload = {
            "tradingsymbol": "SYMBOL",
            "exchange": "NSE",
            "transaction_type": "BUY",
            "quantity": 1,
            "product_type": "CNC",
            "order_type": "MARKET",
            "price": 0,
        }
        auth_token = "test_auth_token"

        response = place_smartorder_api(order_payload, auth_token)

        mock_get_br_symbol.assert_called_once_with("SYMBOL", "NSE")
        self.mock_get_token.assert_called_once_with("NSE", "IBULLS_SYMBOL")
        mock_order_get_api_response.assert_called_once()

        assert response == {"status": "error", "message": "Error placing smart order: Network error"}
        self.mock_logger.exception.assert_called_once_with("Error placing smart order: Network error")

    @patch("app.web.broker.broker.ibulls.api.order_api.get_br_symbol", side_effect=Exception("Symbol lookup error"))
    def test_place_smartorder_api_symbol_lookup_error(self, mock_get_br_symbol):
        order_payload = {
            "tradingsymbol": "SYMBOL",
            "exchange": "NSE",
            "transaction_type": "BUY",
            "quantity": 1,
            "product_type": "CNC",
            "order_type": "MARKET",
            "price": 0,
        }
        auth_token = "test_auth_token"

        response = place_smartorder_api(order_payload, auth_token)

        mock_get_br_symbol.assert_called_once_with("SYMBOL", "NSE")
        assert response == {"status": "error", "message": "Symbol lookup error"}
        self.mock_logger.exception.assert_called_once_with("Error placing smart order: Symbol lookup error")


class TestCloseAllPositions:
    @pytest.fixture(autouse=True)
    def setup(self, mock_logger):
        self.mock_logger = mock_logger[2]  # Use the order_api logger

    @patch("app.web.broker.broker.ibulls.api.order_api.order_get_api_response")
    def test_close_all_positions_success(self, mock_order_get_api_response):
        mock_order_get_api_response.return_value = {
            "type": "success",
            "result": {"message": "Positions closed successfully"}
        }
        auth_token = "test_auth_token"

        response = close_all_positions(auth_token)

        mock_order_get_api_response.assert_called_once()
        assert response == {"status": "success", "message": "Positions closed successfully"}
        self.mock_logger.info.assert_called_once_with("All positions closed successfully.")

    @patch("app.web.broker.broker.ibulls.api.order_api.order_get_api_response")
    def test_close_all_positions_api_error(self, mock_order_get_api_response):
        mock_order_get_api_response.return_value = {
            "type": "error",
            "message": "Failed to close positions"
        }
        auth_token = "test_auth_token"

        response = close_all_positions(auth_token)

        mock_order_get_api_response.assert_called_once()
        assert response == {"status": "error", "message": "Failed to close positions"}
        self.mock_logger.error.assert_called_once_with("Failed to close positions: Failed to close positions")

    @patch("app.web.broker.broker.ibulls.api.order_api.order_get_api_response", side_effect=Exception("Connection error"))
    def test_close_all_positions_exception(self, mock_order_get_api_response):
        auth_token = "test_auth_token"

        response = close_all_positions(auth_token)

        mock_order_get_api_response.assert_called_once()
        assert response == {"status": "error", "message": "Error closing all positions: Connection error"}
        self.mock_logger.exception.assert_called_once_with("Error closing all positions: Connection error")
    @patch("app.web.broker.broker.ibulls.api.order_api.get_api_response", side_effect=Exception("Network error"))
    def test_get_open_position_exception(self, mock_order_get_api_response):
        auth_token = "test_auth_token"
        response = get_open_position(auth_token)

        mock_order_get_api_response.assert_called_once_with("/portfolio/openposition", auth_token)
        assert response == {"status": "error", "message": "Error fetching open positions: Network error"}
        self.mock_logger.exception.assert_called_once_with("Error fetching open positions: Network error")


import json

class TestOrderAPIResponse:
    @pytest.fixture(autouse=True)
    def setup(self, mock_httpx_client, mock_logger):
        self.mock_httpx_client = mock_httpx_client
        self.mock_logger = mock_logger[2] # Use the order_api logger

    def test_get_api_response_get_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"type": "success", "data": "get_data"}

class TestCancelOrder:
    @pytest.fixture(autouse=True)
    def setup(self, mock_logger):
        self.mock_logger = mock_logger[2]  # Use the order_api logger

    @patch("app.web.broker.broker.ibulls.api.order_api.order_get_api_response")
    def test_cancel_order_success(self, mock_order_get_api_response):
        mock_order_get_api_response.return_value = {
            "type": "success",
            "result": {"message": "Order cancelled successfully"}
        }
        order_id = "12345"
        auth_token = "test_auth_token"

        response = cancel_order(order_id, auth_token)

        mock_order_get_api_response.assert_called_once_with(
            "POST", "/api/v1/order/cancel", {"AppOrderID": order_id}, auth_token
        )
        assert response == {"status": "success", "message": "Order cancelled successfully"}
        self.mock_logger.info.assert_called_once_with(f"Order {order_id} cancelled successfully.")

    @patch("app.web.broker.broker.ibulls.api.order_api.order_get_api_response")
    def test_cancel_order_api_error(self, mock_order_get_api_response):
        mock_order_get_api_response.return_value = {
            "type": "error",
            "message": "Failed to cancel order"
        }
        order_id = "12345"
        auth_token = "test_auth_token"

        response = cancel_order(order_id, auth_token)

        mock_order_get_api_response.assert_called_once_with(
            "POST", "/api/v1/order/cancel", {"AppOrderID": order_id}, auth_token
        )
        assert response == {"status": "error", "message": "Failed to cancel order"}
        self.mock_logger.error.assert_called_once_with(f"Failed to cancel order {order_id}: Failed to cancel order")

    @patch("app.web.broker.broker.ibulls.api.order_api.order_get_api_response", side_effect=Exception("Connection error"))
    def test_cancel_order_exception(self, mock_order_get_api_response):
        order_id = "12345"
        auth_token = "test_auth_token"

        response = cancel_order(order_id, auth_token)

        mock_order_get_api_response.assert_called_once_with(
            "POST", "/api/v1/order/cancel", {"AppOrderID": order_id}, auth_token
        )
        assert response == {"status": "error", "message": "Error cancelling order: Connection error"}
        self.mock_logger.exception.assert_called_once_with(f"Error cancelling order {order_id}: Connection error")
        mock_response.text = '{"type": "success", "data": "get_data"}'
        self.mock_httpx_client.get.return_value = mock_response

        response = order_get_api_response("/orders", "test_auth_token", method="GET")

        self.mock_httpx_client.get.assert_called_once_with("http://ibulls.interactive.url/orders", headers={'authorization': 'test_auth_token', 'Content-Type': 'application/json'})
        assert response == {"type": "success", "data": "get_data"}
        self.mock_logger.info.assert_any_call("Response Status Code: 200")
        self.mock_logger.info.assert_any_call('Response Content: {"type": "success", "data": "get_data"}')

    def test_get_api_response_post_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"type": "success", "data": "post_data"}
        mock_response.text = '{"type": "success", "data": "post_data"}'
        self.mock_httpx_client.post.return_value = mock_response

        payload = {"key": "value"}
        response = order_get_api_response("/orders", "test_auth_token", method="POST", payload=payload)

        self.mock_httpx_client.post.assert_called_once_with("http://ibulls.interactive.url/orders", headers={'authorization': 'test_auth_token', 'Content-Type': 'application/json'}, json=payload)
        assert response == {"type": "success", "data": "post_data"}
        self.mock_logger.info.assert_any_call("Response Status Code: 200")
        self.mock_logger.info.assert_any_call('Response Content: {"type": "success", "data": "post_data"}')

    def test_get_api_response_api_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"type": "error", "message": "Bad Request"}
        mock_response.text = '{"type": "error", "message": "Bad Request"}'
        self.mock_httpx_client.post.return_value = mock_response

        payload = {"key": "value"}
        response = order_get_api_response("/orders", "test_auth_token", method="POST", payload=payload)

        assert response == {"type": "error", "message": "Bad Request"}
        self.mock_logger.info.assert_any_call("Response Status Code: 400")
        self.mock_logger.info.assert_any_call('Response Content: {"type": "error", "message": "Bad Request"}')

    def test_get_api_response_exception(self):
        self.mock_httpx_client.get.side_effect = Exception("Network unreachable")

        with pytest.raises(Exception, match="Network unreachable"):
            order_get_api_response("/orders", "test_auth_token", method="GET")

        self.mock_logger.error.assert_called_once_with("Error making API request to /orders: Network unreachable")

    def test_get_api_response_invalid_json_response(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "raw_response", 0)
        mock_response.text = "raw_response"
        self.mock_httpx_client.get.return_value = mock_response

        response = order_get_api_response("/orders", "test_auth_token", method="GET")

        assert response == {"error": "Invalid JSON response from server", "raw_response": "raw_response"}
        self.mock_logger.error.assert_called_once_with("Failed to decode JSON response: Expecting value: line 1 column 1 (char 0)")

    def test_get_api_response_other_method(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"type": "success", "data": "delete_data"}
        mock_response.text = '{"type": "success", "data": "delete_data"}'
        self.mock_httpx_client.request.return_value = mock_response

        response = order_get_api_response("/orders/123", "test_auth_token", method="DELETE")

        self.mock_httpx_client.request.assert_called_once_with("DELETE", "http://ibulls.interactive.url/orders/123", headers={'authorization': 'test_auth_token', 'Content-Type': 'application/json'}, json='')
        assert response == {"type": "success", "data": "delete_data"}
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import Response, Request
from app.web.brokers.ibulls.api.order_api import cancel_order
from app.core.config import settings
from app.utils.logger import logger

class TestCancelOrder:
    @pytest.fixture
    def mock_settings(self):
        with patch('app.core.config.settings', new_callable=MagicMock) as mock_settings:
            mock_settings.IBULLS_API_KEY = "test_api_key"
            mock_settings.IBULLS_USER_ID = "test_user_id"
            mock_settings.IBULLS_PASSWORD = "test_password"
            yield mock_settings

    @pytest.fixture
    def mock_logger(self):
        with patch('app.utils.logger.logger', new_callable=MagicMock) as mock_logger:
            yield mock_logger

    @pytest.fixture
    def mock_httpx_client(self):
        with patch('httpx.AsyncClient', new_callable=AsyncMock) as mock_client:
            yield mock_client

    @pytest.fixture
    def mock_db_session(self):
        with patch('sqlalchemy.ext.asyncio.AsyncSession', new_callable=MagicMock) as mock_session:
            yield mock_session

    @pytest.fixture
    def mock_get_api_response(self):
        with patch('app.web.broker.broker.ibulls.api.order_api.get_api_response', new_callable=AsyncMock) as mock_get_response:
            yield mock_get_response

    @pytest.fixture
    def mock_transform_cancel_order_data(self):
        with patch('app.web.broker.broker.ibulls.api.order_api._transform_cancel_order_data', new_callable=MagicMock) as mock_transform:
            yield mock_transform

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, mock_settings, mock_logger, mock_httpx_client, mock_db_session, mock_get_api_response, mock_transform_cancel_order_data):
        mock_transform_cancel_order_data.return_value = {"Norenordno": "12345"}
        mock_get_api_response.return_value = ({"stat": "Ok", "norenordno": "12345"}, None)

        order_id = "12345"
        token = "test_token"
        user_id = "test_user_id"
        
        response_data, error = await cancel_order(order_id, token, user_id, mock_db_session)

        mock_transform_cancel_order_data.assert_called_once_with(order_id, user_id)
        mock_get_api_response.assert_called_once()
        assert response_data == {"stat": "Ok", "norenordno": "12345"}
        assert error is None
        mock_logger.info.assert_called_with("Order cancellation successful for order_id: 12345")

    @pytest.mark.asyncio
    async def test_cancel_order_api_error(self, mock_settings, mock_logger, mock_httpx_client, mock_db_session, mock_get_api_response, mock_transform_cancel_order_data):
        mock_transform_cancel_order_data.return_value = {"Norenordno": "12345"}
        mock_get_api_response.return_value = (None, "API Error")

        order_id = "12345"
        token = "test_token"
        user_id = "test_user_id"

        response_data, error = await cancel_order(order_id, token, user_id, mock_db_session)

        mock_transform_cancel_order_data.assert_called_once_with(order_id, user_id)
        mock_get_api_response.assert_called_once()
        assert response_data is None
        assert error == "API Error"
        mock_logger.error.assert_called_with("Failed to cancel order 12345: API Error")

    @pytest.mark.asyncio
    async def test_cancel_order_exception(self, mock_settings, mock_logger, mock_httpx_client, mock_db_session, mock_get_api_response, mock_transform_cancel_order_data):
        mock_transform_cancel_order_data.side_effect = Exception("Test Exception")

        order_id = "12345"
        token = "test_token"
        user_id = "test_user_id"

        response_data, error = await cancel_order(order_id, token, user_id, mock_db_session)

        mock_transform_cancel_order_data.assert_called_once_with(order_id, user_id)
        assert response_data is None
        assert "Test Exception" in error
        mock_logger.error.assert_called_with("Exception in cancel_order for order_id 12345: Test Exception")
class TestModifyOrder:
    @pytest.fixture
    def mock_settings(self):
        with patch('app.core.config.settings', new_callable=MagicMock) as mock_settings:
            mock_settings.IBULLS_API_KEY = "test_api_key"
            mock_settings.IBULLS_USER_ID = "test_user_id"
            mock_settings.IBULLS_PASSWORD = "test_password"
            yield mock_settings

    @pytest.fixture
    def mock_logger(self):
        with patch('app.utils.logger.logger', new_callable=MagicMock) as mock_logger:
            yield mock_logger

    @pytest.fixture
    def mock_httpx_client(self):
        with patch('httpx.AsyncClient', new_callable=AsyncMock) as mock_client:
            yield mock_client

    @pytest.fixture
    def mock_db_session(self):
        with patch('sqlalchemy.ext.asyncio.AsyncSession', new_callable=MagicMock) as mock_session:
            yield mock_session

    @pytest.fixture
    def mock_get_api_response(self):
        with patch('app.web.broker.broker.ibulls.api.order_api.get_api_response', new_callable=AsyncMock) as mock_get_response:
            yield mock_get_response

    @pytest.fixture
    def mock_transform_modify_order_data(self):
        with patch('app.web.broker.broker.ibulls.api.order_api._transform_modify_order_data', new_callable=MagicMock) as mock_transform:
            yield mock_transform

    @pytest.mark.asyncio
    async def test_modify_order_success(self, mock_settings, mock_logger, mock_httpx_client, mock_db_session, mock_get_api_response, mock_transform_modify_order_data):
        mock_transform_modify_order_data.return_value = {"Norenordno": "12345", "Qty": 10}
        mock_get_api_response.return_value = ({"stat": "Ok", "norenordno": "12345"}, None)

        order_id = "12345"
        token = "test_token"
        user_id = "test_user_id"
        new_quantity = 10
        
        response_data, error = await modify_order(order_id, new_quantity, token, user_id, mock_db_session)

        mock_transform_modify_order_data.assert_called_once_with(order_id, new_quantity, user_id)
        mock_get_api_response.assert_called_once()
        assert response_data == {"stat": "Ok", "norenordno": "12345"}
        assert error is None
        mock_logger.info.assert_called_with("Order modification successful for order_id: 12345")

    @pytest.mark.asyncio
    async def test_modify_order_api_error(self, mock_settings, mock_logger, mock_httpx_client, mock_db_session, mock_get_api_response, mock_transform_modify_order_data):
        mock_transform_modify_order_data.return_value = {"Norenordno": "12345", "Qty": 10}
        mock_get_api_response.return_value = (None, "API Error")

        order_id = "12345"
        token = "test_token"
        user_id = "test_user_id"
        new_quantity = 10

        response_data, error = await modify_order(order_id, new_quantity, token, user_id, mock_db_session)

        mock_transform_modify_order_data.assert_called_once_with(order_id, new_quantity, user_id)
        mock_get_api_response.assert_called_once()
        assert response_data is None
        assert error == "API Error"
        mock_logger.error.assert_called_with("Failed to modify order 12345: API Error")

    @pytest.mark.asyncio
    async def test_modify_order_exception(self, mock_settings, mock_logger, mock_httpx_client, mock_db_session, mock_get_api_response, mock_transform_modify_order_data):
        mock_transform_modify_order_data.side_effect = Exception("Test Exception")

        order_id = "12345"
        token = "test_token"
        user_id = "test_user_id"
        new_quantity = 10

        response_data, error = await modify_order(order_id, new_quantity, token, user_id, mock_db_session)

        mock_transform_modify_order_data.assert_called_once_with(order_id, new_quantity, user_id)
        assert response_data is None
        assert "Test Exception" in error
        mock_logger.error.assert_called_with("Exception in modify_order for order_id 12345: Test Exception")
class TestCancelAllOrdersAPI:
    @pytest.fixture
    def mock_settings(self):
        with patch('app.core.config.settings', new_callable=MagicMock) as mock_settings:
            mock_settings.IBULLS_API_KEY = "test_api_key"
            mock_settings.IBULLS_USER_ID = "test_user_id"
            mock_settings.IBULLS_PASSWORD = "test_password"
            yield mock_settings

    @pytest.fixture
    def mock_logger(self):
        with patch('app.utils.logger.logger', new_callable=MagicMock) as mock_logger:
            yield mock_logger

    @pytest.fixture
    def mock_httpx_client(self):
        with patch('httpx.AsyncClient', new_callable=AsyncMock) as mock_client:
            yield mock_client

    @pytest.fixture
    def mock_db_session(self):
        with patch('sqlalchemy.ext.asyncio.AsyncSession', new_callable=MagicMock) as mock_session:
            yield mock_session

    @pytest.fixture
    def mock_get_api_response(self):
        with patch('app.web.broker.broker.ibulls.api.order_api.get_api_response', new_callable=AsyncMock) as mock_get_response:
            yield mock_get_response

    @pytest.mark.asyncio
    async def test_cancel_all_orders_success(self, mock_settings, mock_logger, mock_httpx_client, mock_db_session, mock_get_api_response):
        mock_get_api_response.return_value = ({"stat": "Ok"}, None)

        token = "test_token"
        user_id = "test_user_id"
        
        response_data, error = await cancel_all_orders_api(token, user_id, mock_db_session)

        mock_get_api_response.assert_called_once()
        assert response_data == {"stat": "Ok"}
        assert error is None
        mock_logger.info.assert_called_with("All orders cancelled successfully for user_id: test_user_id")

    @pytest.mark.asyncio
    async def test_cancel_all_orders_api_error(self, mock_settings, mock_logger, mock_httpx_client, mock_db_session, mock_get_api_response):
        mock_get_api_response.return_value = (None, "API Error")

        token = "test_token"
        user_id = "test_user_id"

        response_data, error = await cancel_all_orders_api(token, user_id, mock_db_session)

        mock_get_api_response.assert_called_once()
        assert response_data is None
        assert error == "API Error"
        mock_logger.error.assert_called_with("Failed to cancel all orders for user_id test_user_id: API Error")

    @pytest.mark.asyncio
    async def test_cancel_all_orders_exception(self, mock_settings, mock_logger, mock_httpx_client, mock_db_session, mock_get_api_response):
        mock_get_api_response.side_effect = Exception("Test Exception")

        token = "test_token"
        user_id = "test_user_id"

        response_data, error = await cancel_all_orders_api(token, user_id, mock_db_session)

        assert response_data is None
        assert "Test Exception" in error
        mock_logger.error.assert_called_with("Exception in cancel_all_orders_api for user_id test_user_id: Test Exception")