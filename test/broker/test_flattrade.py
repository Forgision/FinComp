import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
import json
import pandas as pd
from datetime import datetime, timedelta

from app.broker.broker.flattrade.api.auth_api import authenticate_broker, authenticate_broker_oauth, sha256_hash
from app.broker.broker.flattrade.api.data import BrokerData, get_api_response
from app.broker.broker.flattrade.api.order_api import (
    place_order_api, cancel_order, modify_order, close_all_positions,
    place_smartorder_api, cancel_all_orders_api, get_order_book, get_trade_book,
    get_positions, get_holdings, get_open_position
)
from app.core.config import settings

# Mock settings for testing
@pytest.fixture(autouse=True)
def mock_settings():
    with patch('app.core.config.settings') as mock_settings:
        mock_settings.BROKER_API_KEY = "mock_api_key_part1:::mock_api_key_part2"
        mock_settings.BROKER_API_SECRET = "mock_api_secret"
        yield mock_settings

# Mock httpx client for all API calls
@pytest.fixture
def mock_httpx_client():
    with patch('app.utils.httpx_client.get_httpx_client') as mock_get_httpx_client:
        mock_client = MagicMock()
        mock_client.post = AsyncMock()
        mock_client.get = AsyncMock()
        mock_client.request = AsyncMock()
        mock_get_httpx_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_get_br_symbol():
    with patch('app.web.broker.broker.flattrade.api.data.get_br_symbol') as mock:
        mock.return_value = "MOCK_SYMBOL"
        yield mock

@pytest.fixture
def mock_get_token():
    with patch('app.web.broker.broker.flattrade.api.data.get_token') as mock:
        mock.return_value = "MOCK_TOKEN"
        yield mock

@pytest.fixture
def mock_get_api_response_data():
    with patch('app.web.broker.broker.flattrade.api.data.get_api_response') as mock:
        yield mock

class TestFlattradeAuth:
    def test_sha256_hash(self):
        assert sha256_hash("test") == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

    @pytest.mark.asyncio
    async def test_authenticate_broker_success(self, mock_settings, mock_httpx_client):
        mock_httpx_client.post.return_value.status_code = 200
        mock_httpx_client.post.return_value.json.return_value = {"stat": "Ok", "token": "mock_auth_token"}

        token, error = await authenticate_broker("mock_code")
        assert token == "mock_auth_token"
        assert error is None
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_broker_api_error_message(self, mock_settings, mock_httpx_client):
        mock_httpx_client.post.return_value.status_code = 200
        mock_httpx_client.post.return_value.json.return_value = {"stat": "Not_Ok", "emsg": "Invalid credentials"}

        token, error = await authenticate_broker("mock_code")
        assert token is None
        assert error == "Invalid credentials"
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_broker_api_error_unknown(self, mock_settings, mock_httpx_client):
        mock_httpx_client.post.return_value.status_code = 200
        mock_httpx_client.post.return_value.json.return_value = {"stat": "Not_Ok"}

        token, error = await authenticate_broker("mock_code")
        assert token is None
        assert error == "Authentication failed without specific error"
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_broker_http_error(self, mock_settings, mock_httpx_client):
        mock_httpx_client.post.return_value.status_code = 400
        mock_httpx_client.post.return_value.json.return_value = {"emsg": "Bad Request"}
        mock_httpx_client.post.return_value.text = "Bad Request"

        token, error = await authenticate_broker("mock_code")
        assert token is None
        assert "API error: Bad Request" in error
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_broker_http_error_no_json(self, mock_settings, mock_httpx_client):
        mock_httpx_client.post.return_value.status_code = 500
        mock_httpx_client.post.return_value.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
        mock_httpx_client.post.return_value.text = "Internal Server Error"

        token, error = await authenticate_broker("mock_code")
        assert token is None
        assert "API error: Status 500, Response: Internal Server Error" in error
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_broker_exception(self, mock_settings):
        with patch('app.web.broker.broker.flattrade.api.auth_api.hashlib.sha256', side_effect=Exception("Hashing error")):
            token, error = await authenticate_broker("mock_code")
            assert token is None
            assert "An exception occurred: Hashing error" in error

    @pytest.mark.asyncio
    async def test_authenticate_broker_oauth_success(self, mock_settings, mock_httpx_client):
        mock_httpx_client.post.return_value.status_code = 200
        mock_httpx_client.post.return_value.json.return_value = {"stat": "Ok", "token": "mock_oauth_token"}

        token, error = await authenticate_broker_oauth("mock_code")
        assert token == "mock_oauth_token"
        assert error is None
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_broker_oauth_api_error_message(self, mock_settings, mock_httpx_client):
        mock_httpx_client.post.return_value.status_code = 200
        mock_httpx_client.post.return_value.json.return_value = {"stat": "Not_Ok", "emsg": "Invalid OAuth"}

        token, error = await authenticate_broker_oauth("mock_code")
        assert token is None
        assert error == "Invalid OAuth"
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_broker_oauth_http_error(self, mock_settings, mock_httpx_client):
        mock_httpx_client.post.return_value.status_code = 401
        mock_httpx_client.post.return_value.json.return_value = {"emsg": "Unauthorized"}

        token, error = await authenticate_broker_oauth("mock_code")
        assert token is None
        assert "API error: Unauthorized" in error
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_broker_oauth_exception(self, mock_settings):
        with patch('app.web.broker.broker.flattrade.api.auth_api.hashlib.sha256', side_effect=Exception("OAuth hashing error")):
            token, error = await authenticate_broker_oauth("mock_code")
            assert token is None
            assert "An exception occurred: OAuth hashing error" in error

class TestFlattradeData:
    @pytest.mark.asyncio
    async def test_get_api_response_success(self, mock_settings, mock_httpx_client):
        mock_httpx_client.request.return_value.text = '{"stat": "Ok", "data": "test_data"}'
        response = get_api_response("/test_endpoint", "mock_auth_token", method="POST", payload={"key": "value"})
        assert response == {"stat": "Ok", "data": "test_data"}
        mock_httpx_client.request.assert_called_once()
        assert mock_httpx_client.request.call_args[0][0] == "POST"
        assert mock_httpx_client.request.call_args[0][1] == "https://piconnect.flattrade.in/test_endpoint"
        assert "jData=" in mock_httpx_client.request.call_args[1]["content"]
        assert "jKey=mock_auth_token" in mock_httpx_client.request.call_args[1]["content"]

    @pytest.mark.asyncio
    async def test_get_api_response_no_payload(self, mock_settings, mock_httpx_client):
        mock_httpx_client.request.return_value.text = '{"stat": "Ok", "data": "test_data"}'
        response = get_api_response("/test_endpoint", "mock_auth_token", method="POST")
        assert response == {"stat": "Ok", "data": "test_data"}
        mock_httpx_client.request.assert_called_once()
        assert "jData=" in mock_httpx_client.request.call_args[1]["content"]
        assert f'"uid": "{mock_settings.BROKER_API_KEY.split(":::")[0]}"' in mock_httpx_client.request.call_args[1]["content"]

    @pytest.mark.asyncio
    async def test_get_api_response_json_decode_error(self, mock_settings, mock_httpx_client):
        mock_httpx_client.request.return_value.text = 'invalid json'
        with pytest.raises(json.JSONDecodeError):
            get_api_response("/test_endpoint", "mock_auth_token", method="POST")

    @pytest.mark.asyncio
    async def test_broker_data_get_quotes_success(self, mock_get_br_symbol, mock_get_token, mock_get_api_response_data):
        mock_get_api_response_data.return_value = {
            "stat": "Ok", "bp1": 100.0, "sp1": 101.0, "o": 90.0, "h": 110.0, "l": 80.0,
            "lp": 105.0, "c": 95.0, "v": 1000.0, "oi": 500
        }
        broker_data = BrokerData("mock_auth_token")
        quotes = broker_data.get_quotes("TEST", "NSE")
        assert quotes == {
            'bid': 100.0, 'ask': 101.0, 'open': 90.0, 'high': 110.0, 'low': 80.0,
            'ltp': 105.0, 'prev_close': 95.0, 'volume': 1000, 'oi': 500
        }
        mock_get_br_symbol.assert_called_once_with("TEST", "NSE")
        mock_get_token.assert_called_once_with("TEST", "NSE")
        mock_get_api_response_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_broker_data_get_quotes_api_error(self, mock_get_br_symbol, mock_get_token, mock_get_api_response_data):
        mock_get_api_response_data.return_value = {"stat": "Not_Ok", "emsg": "API Error"}
        broker_data = BrokerData("mock_auth_token")
        with pytest.raises(Exception, match="Error from Flattrade API: API Error"):
            broker_data.get_quotes("TEST", "NSE")

    @pytest.mark.asyncio
    async def test_broker_data_get_quotes_exception(self, mock_get_br_symbol):
        mock_get_br_symbol.side_effect = Exception("Symbol lookup error")
        broker_data = BrokerData("mock_auth_token")
        with pytest.raises(Exception, match="Error fetching quotes: Symbol lookup error"):
            broker_data.get_quotes("TEST", "NSE")

    @pytest.mark.asyncio
    async def test_broker_data_get_depth_success(self, mock_get_br_symbol, mock_get_token, mock_get_api_response_data):
        mock_get_api_response_data.return_value = {
            "stat": "Ok", "bp1": 99.0, "bq1": 100, "bo1": 10, "sp1": 101.0, "sq1": 150, "so1": 15,
            "bp2": 98.0, "bq2": 200, "bo2": 20, "sp2": 102.0, "sq2": 250, "so2": 25,
            "h": 110.0, "l": 80.0, "lp": 100.0, "ltq": 50, "o": 90.0, "c": 95.0, "v": 1000.0, "oi": 500
        }
        broker_data = BrokerData("mock_auth_token")
        depth = broker_data.get_depth("TEST", "NSE")
        assert depth['ltp'] == 100.0
        assert depth['oi'] == 500
        assert len(depth['bids']) == 5
        assert depth['bids'][0]['price'] == 99.0
        assert depth['bids'][0]['quantity'] == 100
        assert depth['bids'][0]['orders'] == 10
        assert depth['asks'][0]['price'] == 101.0
        assert depth['asks'][0]['quantity'] == 150
        assert depth['asks'][0]['orders'] == 15
        assert depth['totalbuyqty'] == 300 # 100 + 200
        assert depth['totalsellqty'] == 400 # 150 + 250
        mock_get_br_symbol.assert_called_once_with("TEST", "NSE")
        mock_get_token.assert_called_once_with("TEST", "NSE")
        mock_get_api_response_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_broker_data_get_depth_api_error(self, mock_get_br_symbol, mock_get_token, mock_get_api_response_data):
        mock_get_api_response_data.return_value = {"stat": "Not_Ok", "emsg": "API Error"}
        broker_data = BrokerData("mock_auth_token")
        with pytest.raises(Exception, match="Error from Flattrade API: API Error"):
            broker_data.get_depth("TEST", "NSE")

    @pytest.mark.asyncio
    async def test_broker_data_get_depth_exception(self, mock_get_br_symbol):
        mock_get_br_symbol.side_effect = Exception("Symbol lookup error")
        broker_data = BrokerData("mock_auth_token")
        with pytest.raises(Exception, match="Error fetching market depth: Symbol lookup error"):
            broker_data.get_depth("TEST", "NSE")

    def test_broker_data_get_intervals(self):
        broker_data = BrokerData("mock_auth_token")
        intervals = broker_data.get_intervals()
        assert isinstance(intervals, list)
        assert "1m" in intervals
        assert "D" in intervals
        assert "1h" in intervals

    @pytest.mark.asyncio
    async def test_broker_data_get_history_unsupported_interval(self):
        broker_data = BrokerData("mock_auth_token")
        with pytest.raises(Exception, match="Unsupported interval 'UNKNOWN'"):
            broker_data.get_history("TEST", "NSE", "UNKNOWN", "2023-01-01", "2023-01-02")

    @pytest.mark.asyncio
    async def test_broker_data_get_history_daily_success(self, mock_get_br_symbol, mock_get_token, mock_get_api_response_data):
        mock_get_api_response_data.return_value = [
            {"ssboe": 1672531200, "into": 100, "inth": 110, "intl": 90, "intc": 105, "intv": 1000, "oi": 500},
            {"ssboe": 1672617600, "into": 105, "inth": 115, "intl": 95, "intc": 110, "intv": 1200, "oi": 600},
        ]
        broker_data = BrokerData("mock_auth_token")
        df = broker_data.get_history("TEST", "NSE", "D", "2023-01-01", "2023-01-02")

        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert len(df) == 2
        assert df["open"].iloc[0] == 100
        assert df["close"].iloc[1] == 110
        assert df["timestamp"].iloc[0] == 1672531200
        mock_get_api_response_data.assert_called_once_with("/PiConnectTP/EODChartData", "mock_auth_token", payload=pytest.ANY)

    @pytest.mark.asyncio
    async def test_broker_data_get_history_intraday_success(self, mock_get_br_symbol, mock_get_token, mock_get_api_response_data):
        mock_get_api_response_data.return_value = [
            {"time": "01-01-2023 09:15:00", "into": 100, "inth": 102, "intl": 99, "intc": 101, "intv": 100, "oi": 10},
            {"time": "01-01-2023 09:20:00", "into": 101, "inth": 103, "intl": 100, "intc": 102, "intv": 120, "oi": 12},
        ]
        broker_data = BrokerData("mock_auth_token")
        df = broker_data.get_history("TEST", "NSE", "5m", "2023-01-01", "2023-01-01")

        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert len(df) == 2
        assert df["open"].iloc[0] == 100
        assert df["close"].iloc[1] == 102
        mock_get_api_response_data.assert_called_once_with("/PiConnectTP/TPSeries", "mock_auth_token", payload=pytest.ANY)

    @pytest.mark.asyncio
    async def test_broker_data_get_history_api_error(self, mock_get_br_symbol, mock_get_token, mock_get_api_response_data):
        mock_get_api_response_data.return_value = {"stat": "Not_Ok", "emsg": "API Error"}
        broker_data = BrokerData("mock_auth_token")
        with pytest.raises(Exception, match="Error from Flattrade API: API Error"):
            broker_data.get_history("TEST", "NSE", "D", "2023-01-01", "2023-01-02")

    @pytest.mark.asyncio
    async def test_broker_data_get_history_invalid_response_format(self, mock_get_br_symbol, mock_get_token, mock_get_api_response_data):
        mock_get_api_response_data.return_value = "invalid response"
        broker_data = BrokerData("mock_auth_token")
        with pytest.raises(Exception, match="Invalid response format from Flattrade API"):
            broker_data.get_history("TEST", "NSE", "D", "2023-01-01", "2023-01-02")

    @pytest.mark.asyncio
    async def test_broker_data_get_history_empty_data_response(self, mock_get_br_symbol, mock_get_token, mock_get_api_response_data):
        mock_get_api_response_data.return_value = []
        broker_data = BrokerData("mock_auth_token")
        df = broker_data.get_history("TEST", "NSE", "D", "2023-01-01", "2023-01-02")
        assert df.empty

    @pytest.mark.asyncio
    async def test_broker_data_get_history_daily_with_today_quotes(self, mock_get_br_symbol, mock_get_token, mock_get_api_response_data):
        # Mock historical data to be empty up to yesterday
        mock_get_api_response_data.side_effect = [
            [], # for historical data
            {
                "stat": "Ok", "bp1": 100.0, "sp1": 101.0, "o": 90.0, "h": 110.0, "l": 80.0,
                "lp": 105.0, "c": 95.0, "v": 1000.0, "oi": 500
            } # for get_quotes
        ]
        broker_data = BrokerData("mock_auth_token")

        # Set dates to include today
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        df = broker_data.get_history("TEST", "NSE", "D", yesterday, today)

        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert len(df) == 1 # Only today's data from quotes
        assert df["open"].iloc[0] == 90.0
        assert df["close"].iloc[0] == 105.0

class TestFlattradeOrder:
    @pytest.mark.asyncio
    async def test_get_order_book_success(self, mock_httpx_client, mock_settings):
        mock_httpx_client.request.return_value.text = json.dumps([
            {"norenordno": "123", "tsym": "TEST", "status": "OPEN"},
            {"norenordno": "456", "tsym": "TEST2", "status": "COMPLETE"}
        ])
        order_book = get_order_book("mock_auth_token")
        assert len(order_book) == 2
        assert order_book[0]["norenordno"] == "123"
        mock_httpx_client.request.assert_called_once_with(
            "POST",
            "https://piconnect.flattrade.in/PiConnectTP/OrderBook",
            content=pytest.ANY,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

    @pytest.mark.asyncio
    async def test_get_order_book_empty(self, mock_httpx_client, mock_settings):
        mock_httpx_client.request.return_value.text = json.dumps([])
        order_book = get_order_book("mock_auth_token")
        assert order_book == []

    @pytest.mark.asyncio
    async def test_get_order_book_api_error(self, mock_httpx_client, mock_settings):
        mock_httpx_client.request.return_value.text = json.dumps({"stat": "Not_Ok", "emsg": "API Error"})
        order_book = get_order_book("mock_auth_token")
        assert order_book == {"stat": "Not_Ok", "emsg": "API Error"}

    @pytest.mark.asyncio
    async def test_get_trade_book_success(self, mock_httpx_client, mock_settings):
        mock_httpx_client.request.return_value.text = json.dumps([
            {"norenordno": "123", "tsym": "TEST", "qty": "10"},
            {"norenordno": "456", "tsym": "TEST2", "qty": "20"}
        ])
        trade_book = get_trade_book("mock_auth_token")
        assert len(trade_book) == 2
        assert trade_book[0]["tsym"] == "TEST"
        mock_httpx_client.request.assert_called_once_with(
            "POST",
            "https://piconnect.flattrade.in/PiConnectTP/TradeBook",
            content=pytest.ANY,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

    @pytest.mark.asyncio
    async def test_get_trade_book_empty(self, mock_httpx_client, mock_settings):
        mock_httpx_client.request.return_value.text = json.dumps([])
        trade_book = get_trade_book("mock_auth_token")
        assert trade_book == []

    @pytest.mark.asyncio
    async def test_get_positions_success(self, mock_httpx_client, mock_settings):
        mock_httpx_client.request.return_value.text = json.dumps([
            {"tsym": "TEST", "netqty": "10"},
            {"tsym": "TEST2", "netqty": "-5"}
        ])
        positions = get_positions("mock_auth_token")
        assert len(positions) == 2
        assert positions[0]["tsym"] == "TEST"
        mock_httpx_client.request.assert_called_once_with(
            "POST",
            "https://piconnect.flattrade.in/PiConnectTP/PositionBook",
            content=pytest.ANY,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

    @pytest.mark.asyncio
    async def test_get_positions_empty(self, mock_httpx_client, mock_settings):
        mock_httpx_client.request.return_value.text = json.dumps([])
        positions = get_positions("mock_auth_token")
        assert positions == []

    @pytest.mark.asyncio
    async def test_get_holdings_success(self, mock_httpx_client, mock_settings):
        mock_httpx_client.request.return_value.text = json.dumps([
            {"isin": "INE000A01025", "holdqty": "100"},
            {"isin": "INE000B01026", "holdqty": "200"}
        ])
        holdings = get_holdings("mock_auth_token")
        assert len(holdings) == 2
        assert holdings[0]["isin"] == "INE000A01025"
        mock_httpx_client.request.assert_called_once_with(
            "POST",
            "https://piconnect.flattrade.in/PiConnectTP/Holdings",
            content=pytest.ANY,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

    @pytest.mark.asyncio
    async def test_get_holdings_empty(self, mock_httpx_client, mock_settings):
        mock_httpx_client.request.return_value.text = json.dumps([])
        holdings = get_holdings("mock_auth_token")
        assert holdings == []

    @pytest.mark.asyncio
    async def test_get_open_position_found(self, mock_get_br_symbol):
        with patch('app.web.broker.broker.flattrade.api.order_api.get_positions') as mock_get_positions:
            mock_get_positions.return_value = [
                {"tsym": "TEST", "exch": "NSE", "prd": "C", "netqty": "5"},
                {"tsym": "OTHER", "exch": "NSE", "prd": "C", "netqty": "10"}
            ]
            net_qty = get_open_position("TEST", "NSE", "C", "mock_auth_token")
            assert net_qty == "5"
            mock_get_br_symbol.assert_called_once_with("TEST", "NSE")
            mock_get_positions.assert_called_once_with("mock_auth_token")

    @pytest.mark.asyncio
    async def test_get_open_position_not_found(self, mock_get_br_symbol):
        with patch('app.web.broker.broker.flattrade.api.order_api.get_positions') as mock_get_positions:
            mock_get_positions.return_value = [
                {"tsym": "OTHER", "exch": "NSE", "prd": "C", "netqty": "10"}
            ]
            net_qty = get_open_position("TEST", "NSE", "C", "mock_auth_token")
            assert net_qty == "0"

    @pytest.mark.asyncio
    async def test_get_open_position_empty_positions(self, mock_get_br_symbol):
        with patch('app.web.broker.broker.flattrade.api.order_api.get_positions') as mock_get_positions:
            mock_get_positions.return_value = []
            net_qty = get_open_position("TEST", "NSE", "C", "mock_auth_token")
            assert net_qty == "0"

    @pytest.mark.asyncio
    async def test_get_open_position_api_error(self, mock_get_br_symbol):
        with patch('app.web.broker.broker.flattrade.api.order_api.get_positions') as mock_get_positions:
            mock_get_positions.return_value = {"stat": "Not_Ok", "emsg": "API Error"}
            net_qty = get_open_position("TEST", "NSE", "C", "mock_auth_token")
            assert net_qty == "0"

    @pytest.mark.asyncio
    async def test_place_order_api_success(self, mock_httpx_client, mock_settings):
        mock_httpx_client.post.return_value.status_code = 200
        mock_httpx_client.post.return_value.json.return_value = {"stat": "Ok", "norenordno": "ORDER123"}
        with patch('app.web.broker.broker.flattrade.api.order_api.get_token', return_value="MOCK_TOKEN"), \
             patch('app.web.broker.broker.flattrade.api.order_api.transform_data', return_value={"transformed": "data"}):
            
            order_data = {"symbol": "TEST", "exchange": "NSE", "quantity": 1, "action": "BUY", "pricetype": "MARKET", "product": "MIS"}
            res, response_data, orderid = await place_order_api(order_data, "mock_auth_token")

            assert res.status == 200
            assert response_data["norenordno"] == "ORDER123"
            assert orderid == "ORDER123"
            mock_httpx_client.post.assert_called_once()
            assert "jData=" in mock_httpx_client.post.call_args[1]["content"]
            assert "jKey=mock_auth_token" in mock_httpx_client.post.call_args[1]["content"]

    @pytest.mark.asyncio
    async def test_place_order_api_failure(self, mock_httpx_client, mock_settings):
        mock_httpx_client.post.return_value.status_code = 200
        mock_httpx_client.post.return_value.json.return_value = {"stat": "Not_Ok", "emsg": "Order rejected"}
        with patch('app.web.broker.broker.flattrade.api.order_api.get_token', return_value="MOCK_TOKEN"), \
             patch('app.web.broker.broker.flattrade.api.order_api.transform_data', return_value={"transformed": "data"}):
            
            order_data = {"symbol": "TEST", "exchange": "NSE", "quantity": 1, "action": "BUY", "pricetype": "MARKET", "product": "MIS"}
            res, response_data, orderid = await place_order_api(order_data, "mock_auth_token")

            assert res.status == 200
            assert response_data["emsg"] == "Order rejected"
            assert orderid is None

    @pytest.mark.asyncio
    async def test_place_order_api_http_error(self, mock_httpx_client, mock_settings):
        mock_httpx_client.post.return_value.status_code = 500
        mock_httpx_client.post.return_value.json.return_value = {"emsg": "Internal Server Error"}
        with patch('app.web.broker.broker.flattrade.api.order_api.get_token', return_value="MOCK_TOKEN"), \
             patch('app.web.broker.broker.flattrade.api.order_api.transform_data', return_value={"transformed": "data"}):
            
            order_data = {"symbol": "TEST", "exchange": "NSE", "quantity": 1, "action": "BUY", "pricetype": "MARKET", "product": "MIS"}
            res, response_data, orderid = await place_order_api(order_data, "mock_auth_token")

            assert res.status == 500
            assert response_data["emsg"] == "Internal Server Error"
            assert orderid is None

    @pytest.mark.asyncio
    async def test_place_smartorder_api_no_action_needed(self):
        with patch('app.web.broker.broker.flattrade.api.order_api.get_open_position', return_value="5"), \
             patch('app.web.broker.broker.flattrade.api.order_api.map_product_type', return_value="C"):
            
            data = {"symbol": "TEST", "exchange": "NSE", "product": "CNC", "position_size": "5", "quantity": "0"}
            res, response, orderid = await place_smartorder_api(data, "mock_auth_token")
            assert res is None
            assert "No action needed" in response["message"]
            assert orderid is None

    @pytest.mark.asyncio
    async def test_place_smartorder_api_exit_position(self):
        with patch('app.web.broker.broker.flattrade.api.order_api.get_open_position', return_value="5"), \
             patch('app.web.broker.broker.flattrade.api.order_api.map_product_type', return_value="C"), \
             patch('app.web.broker.broker.flattrade.api.order_api.place_order_api', new_callable=AsyncMock) as mock_place_order_api:
            
            mock_place_order_api.return_value = (MagicMock(status=200), {"stat": "Ok", "norenordno": "EXIT123"}, "EXIT123")
            data = {"symbol": "TEST", "exchange": "NSE", "product": "CNC", "position_size": "0", "quantity": "0"}
            res, response, orderid = await place_smartorder_api(data, "mock_auth_token")

            assert res.status == 200
            assert orderid == "EXIT123"
            mock_place_order_api.assert_called_once()
            assert mock_place_order_api.call_args[0][0]["action"] == "SELL"
            assert mock_place_order_api.call_args[0][0]["quantity"] == "5"

    @pytest.mark.asyncio
    async def test_place_smartorder_api_enter_position(self):
        with patch('app.web.broker.broker.flattrade.api.order_api.get_open_position', return_value="0"), \
             patch('app.web.broker.broker.flattrade.api.order_api.map_product_type', return_value="C"), \
             patch('app.web.broker.broker.flattrade.api.order_api.place_order_api', new_callable=AsyncMock) as mock_place_order_api:
            
            mock_place_order_api.return_value = (MagicMock(status=200), {"stat": "Ok", "norenordno": "ENTER123"}, "ENTER123")
            data = {"symbol": "TEST", "exchange": "NSE", "product": "CNC", "position_size": "10", "quantity": "10", "action": "BUY"}
            res, response, orderid = await place_smartorder_api(data, "mock_auth_token")

            assert res.status == 200
            assert orderid == "ENTER123"
            mock_place_order_api.assert_called_once()
            assert mock_place_order_api.call_args[0][0]["action"] == "BUY"
            assert mock_place_order_api.call_args[0][0]["quantity"] == "10"

    @pytest.mark.asyncio
    async def test_place_smartorder_api_increase_long_position(self):
        with patch('app.web.broker.broker.flattrade.api.order_api.get_open_position', return_value="5"), \
             patch('app.web.broker.broker.flattrade.api.order_api.map_product_type', return_value="C"), \
             patch('app.web.broker.broker.flattrade.api.order_api.place_order_api', new_callable=AsyncMock) as mock_place_order_api:
            
            mock_place_order_api.return_value = (MagicMock(status=200), {"stat": "Ok", "norenordno": "INC123"}, "INC123")
            data = {"symbol": "TEST", "exchange": "NSE", "product": "CNC", "position_size": "15", "quantity": "15", "action": "BUY"}
            res, response, orderid = await place_smartorder_api(data, "mock_auth_token")

            assert res.status == 200
            assert orderid == "INC123"
            mock_place_order_api.assert_called_once()
            assert mock_place_order_api.call_args[0][0]["action"] == "BUY"
            assert mock_place_order_api.call_args[0][0]["quantity"] == "10" # 15 - 5

    @pytest.mark.asyncio
    async def test_place_smartorder_api_decrease_long_position(self):
        with patch('app.web.broker.broker.flattrade.api.order_api.get_open_position', return_value="10"), \
             patch('app.web.broker.broker.flattrade.api.order_api.map_product_type', return_value="C"), \
             patch('app.web.broker.broker.flattrade.api.order_api.place_order_api', new_callable=AsyncMock) as mock_place_order_api:
            
            mock_place_order_api.return_value = (MagicMock(status=200), {"stat": "Ok", "norenordno": "DEC123"}, "DEC123")
            data = {"symbol": "TEST", "exchange": "NSE", "product": "CNC", "position_size": "5", "quantity": "5", "action": "SELL"}
            res, response, orderid = await place_smartorder_api(data, "mock_auth_token")

            assert res.status == 200
            assert orderid == "DEC123"
            mock_place_order_api.assert_called_once()
            assert mock_place_order_api.call_args[0][0]["action"] == "SELL"
            assert mock_place_order_api.call_args[0][0]["quantity"] == "5" # 10 - 5

    @pytest.mark.asyncio
    async def test_close_all_positions_success(self, mock_settings):
        with patch('app.web.broker.broker.flattrade.api.order_api.get_positions') as mock_get_positions, \
             patch('app.web.broker.broker.flattrade.api.order_api.get_symbol', return_value="MOCK_SYMBOL"), \
             patch('app.web.broker.broker.flattrade.api.order_api.place_order_api', new_callable=AsyncMock) as mock_place_order_api, \
             patch('app.web.broker.broker.flattrade.api.order_api.reverse_map_product_type', return_value="CNC"):
            
            mock_get_positions.return_value = [
                {"tsym": "TEST1", "exch": "NSE", "prd": "C", "netqty": "10", "token": "12345"},
                {"tsym": "TEST2", "exch": "NSE", "prd": "C", "netqty": "-5", "token": "67890"},
                {"tsym": "TEST3", "exch": "NSE", "prd": "C", "netqty": "0", "token": "11223"}
            ]
            mock_place_order_api.return_value = (MagicMock(status=200), {"stat": "Ok", "norenordno": "SQOFF123"}, "SQOFF123")
            
            response, status_code = await close_all_positions("mock_api_key", "mock_auth_token")

            assert status_code == 200
            assert response["message"] == "All Open Positions SquaredOff"
            assert mock_place_order_api.call_count == 2
            # Check calls for TEST1 (SELL 10)
            assert mock_place_order_api.call_args_list[0][0][0]["action"] == "SELL"
            assert mock_place_order_api.call_args_list[0][0][0]["quantity"] == "10"
            # Check calls for TEST2 (BUY 5)
            assert mock_place_order_api.call_args_list[1][0][0]["action"] == "BUY"
            assert mock_place_order_api.call_args_list[1][0][0]["quantity"] == "5"

    @pytest.mark.asyncio
    async def test_close_all_positions_no_open_positions(self, mock_settings):
        with patch('app.web.broker.broker.flattrade.api.order_api.get_positions') as mock_get_positions:
            mock_get_positions.return_value = [{"stat": "Not_Ok"}]
            response, status_code = await close_all_positions("mock_api_key", "mock_auth_token")
            assert status_code == 200
            assert response["message"] == "No Open Positions Found"

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, mock_httpx_client, mock_settings):
        mock_httpx_client.post.return_value.status_code = 200
        mock_httpx_client.post.return_value.json.return_value = {"stat": "Ok"}

        response, status_code = await cancel_order("ORDER123", "mock_auth_token")
        assert status_code == 200
        assert response["status"] == "success"
        assert response["orderid"] == "ORDER123"
        mock_httpx_client.post.assert_called_once()
        assert "norenordno=%22ORDER123%22" in mock_httpx_client.post.call_args[1]["content"]

    @pytest.mark.asyncio
    async def test_cancel_order_failure(self, mock_httpx_client, mock_settings):
        mock_httpx_client.post.return_value.status_code = 200
        mock_httpx_client.post.return_value.json.return_value = {"stat": "Not_Ok", "emsg": "Order not found"}

        response, status_code = await cancel_order("ORDER123", "mock_auth_token")
        assert status_code == 200
        assert response["status"] == "error"
        assert response["message"] == "Order not found"

    @pytest.mark.asyncio
    async def test_cancel_order_http_error(self, mock_httpx_client, mock_settings):
        mock_httpx_client.post.return_value.status_code = 400
        mock_httpx_client.post.return_value.json.return_value = {"emsg": "Bad Request"}

        response, status_code = await cancel_order("ORDER123", "mock_auth_token")
        assert status_code == 400
        assert response["status"] == "error"
        assert response["message"] == "Bad Request"

    @pytest.mark.asyncio
    async def test_modify_order_success(self, mock_httpx_client, mock_settings):
        mock_httpx_client.post.return_value.status_code = 200
        mock_httpx_client.post.return_value.json.return_value = {"stat": "Ok"}
        with patch('app.web.broker.broker.flattrade.api.order_api.get_token', return_value="MOCK_TOKEN"), \
             patch('app.web.broker.broker.flattrade.api.order_api.get_br_symbol', return_value="MOCK_BR_SYMBOL"), \
             patch('app.web.broker.broker.flattrade.api.order_api.transform_modify_order_data', return_value={"transformed": "modify_data"}):
            
            modify_data = {"orderid": "ORDER123", "symbol": "TEST", "exchange": "NSE", "quantity": 5}
            response, status_code = await modify_order(modify_data, "mock_auth_token")

            assert status_code == 200
            assert response["status"] == "success"
            assert response["orderid"] == "ORDER123"
            mock_httpx_client.post.assert_called_once()
            assert "jData=" in mock_httpx_client.post.call_args[1]["content"]
            assert "jKey=mock_auth_token" in mock_httpx_client.post.call_args[1]["content"]

    @pytest.mark.asyncio
    async def test_modify_order_failure(self, mock_httpx_client, mock_settings):
        mock_httpx_client.post.return_value.status_code = 200
        mock_httpx_client.post.return_value.json.return_value = {"stat": "Not_Ok", "emsg": "Modification failed"}
        with patch('app.web.broker.broker.flattrade.api.order_api.get_token', return_value="MOCK_TOKEN"), \
             patch('app.web.broker.broker.flattrade.api.order_api.get_br_symbol', return_value="MOCK_BR_SYMBOL"), \
             patch('app.web.broker.broker.flattrade.api.order_api.transform_modify_order_data', return_value={"transformed": "modify_data"}):
            
            modify_data = {"orderid": "ORDER123", "symbol": "TEST", "exchange": "NSE", "quantity": 5}
            response, status_code = await modify_order(modify_data, "mock_auth_token")

            assert status_code == 200
            assert response["status"] == "error"
            assert response["message"] == "Modification failed"

    @pytest.mark.asyncio
    async def test_cancel_all_orders_api_success(self, mock_settings):
        with patch('app.web.broker.broker.flattrade.api.order_api.get_order_book') as mock_get_order_book, \
             patch('app.web.broker.broker.flattrade.api.order_api.cancel_order', new_callable=AsyncMock) as mock_cancel_order:
            
            mock_get_order_book.return_value = [
                {"norenordno": "OPEN1", "status": "OPEN"},
                {"norenordno": "PENDING2", "status": "TRIGGER_PENDING"},
                {"norenordno": "COMPLETE3", "status": "COMPLETE"}
            ]
            mock_cancel_order.side_effect = [
                ({"status": "success", "orderid": "OPEN1"}, 200),
                ({"status": "success", "orderid": "PENDING2"}, 200)
            ]

            canceled_orders, failed_cancellations = await cancel_all_orders_api({}, "mock_auth_token")

            assert canceled_orders == ["OPEN1", "PENDING2"]
            assert failed_cancellations == []
            assert mock_get_order_book.called
            assert mock_cancel_order.call_count == 2

    @pytest.mark.asyncio
    async def test_cancel_all_orders_api_some_failures(self, mock_settings):
        with patch('app.web.broker.broker.flattrade.api.order_api.get_order_book') as mock_get_order_book, \
             patch('app.web.broker.broker.flattrade.api.order_api.cancel_order', new_callable=AsyncMock) as mock_cancel_order:
            
            mock_get_order_book.return_value = [
                {"norenordno": "OPEN1", "status": "OPEN"},
                {"norenordno": "PENDING2", "status": "TRIGGER_PENDING"},
                {"norenordno": "OPEN3", "status": "OPEN"}
            ]
            mock_cancel_order.side_effect = [
                ({"status": "success", "orderid": "OPEN1"}, 200),
                ({"status": "error", "message": "Failed"}, 400),
                ({"status": "success", "orderid": "OPEN3"}, 200)
            ]

            canceled_orders, failed_cancellations = await cancel_all_orders_api({}, "mock_auth_token")

            assert canceled_orders == ["OPEN1", "OPEN3"]
            assert failed_cancellations == ["PENDING2"] # Note: cancel_order returns orderid on success, but not on failure
            assert mock_get_order_book.called
            assert mock_cancel_order.call_count == 3

    @pytest.mark.asyncio
    async def test_cancel_all_orders_api_no_orders_to_cancel(self, mock_settings):
        with patch('app.web.broker.broker.flattrade.api.order_api.get_order_book', return_value=[]) as mock_get_order_book, \
             patch('app.web.broker.broker.flattrade.api.order_api.cancel_order', new_callable=AsyncMock) as mock_cancel_order:
            
            canceled_orders, failed_cancellations = await cancel_all_orders_api({}, "mock_auth_token")

            assert canceled_orders == []
            assert failed_cancellations == []
            assert mock_get_order_book.called
            assert not mock_cancel_order.called
