import pytest
pytest.skip("Skipped by user request", allow_module_level=True)
from unittest.mock import MagicMock, patch

import pytest

from app.web.brokers.fivepaisaxts.api.auth_api import (
    authenticate_broker,
    get_feed_token,
)
from app.web.brokers.fivepaisaxts.api.data import BrokerData, get_api_response
from app.web.brokers.fivepaisaxts.api.order_api import (
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
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.BROKER_API_KEY = "mock_api_key"
        mock_settings.BROKER_API_SECRET = "mock_api_secret"
        mock_settings.BROKER_API_KEY_MARKET = "mock_market_api_key"
        mock_settings.BROKER_API_SECRET_MARKET = "mock_market_api_secret"
        yield mock_settings


@pytest.fixture
def mock_httpx_client():
    with patch("app.utils.httpx_client.get_httpx_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_auth_token_db():
    with patch(
        "app.web.brokers.fivepaisaxts.api.auth_api.get_feed_token"
    ) as mock_get_feed_token:
        yield mock_get_feed_token


@pytest.fixture
def mock_token_db():
    with patch(
        "app.web.brokers.fivepaisaxts.api.order_api.get_token"
    ) as mock_get_token:
        yield mock_get_token


@pytest.fixture
def mock_get_br_symbol():
    with patch(
        "app.web.brokers.fivepaisaxts.api.order_api.get_br_symbol"
    ) as mock_get_br_symbol:
        mock_get_br_symbol.return_value = "BR_SYMBOL"
        yield mock_get_br_symbol


@pytest.fixture
def mock_transform_data():
    with patch(
        "app.web.brokers.fivepaisaxts.mapping.transform_data.transform_data"
    ) as mock_transform:
        mock_transform.return_value = {"transformed": "data"}
        yield mock_transform


@pytest.fixture
def mock_transform_modify_order_data():
    with patch(
        "app.web.brokers.fivepaisaxts.mapping.transform_data.transform_modify_order_data"
    ) as mock_transform:
        mock_transform.return_value = {"transformed_modify": "data"}
        yield mock_transform


@pytest.fixture
def mock_map_product_type():
    with patch(
        "app.web.brokers.fivepaisaxts.mapping.transform_data.map_product_type"
    ) as mock_map:
        mock_map.return_value = "MAPPED_PRODUCT_TYPE"
        yield mock_map


class TestFivepaisaXTSAuth:
    @pytest.mark.asyncio
    async def test_authenticate_broker_success(
        self, mock_settings, mock_httpx_client, mock_auth_token_db
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "type": "success",
            "result": {"token": "mock_auth_token_result"},
        }
        mock_httpx_client.post.return_value = mock_response

        mock_auth_token_db.return_value = ("mock_feed_token", "mock_user_id", None)

        token, feed_token, user_id, error = authenticate_broker("mock_request_token")

        assert token == "mock_auth_token_result"
        assert feed_token == "mock_feed_token"
        assert user_id == "mock_user_id"
        assert error is None
        mock_httpx_client.post.assert_called_once()
        mock_auth_token_db.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_broker_api_error(
        self, mock_settings, mock_httpx_client, mock_auth_token_db
    ):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"message": "API error"}
        mock_httpx_client.post.return_value = mock_response

        token, feed_token, user_id, error = authenticate_broker("mock_request_token")

        assert token is None
        assert feed_token is None
        assert user_id is None
        assert "API error" in error
        mock_httpx_client.post.assert_called_once()
        mock_auth_token_db.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_broker_exception(
        self, mock_settings, mock_httpx_client, mock_auth_token_db
    ):
        mock_httpx_client.post.side_effect = Exception("Network error")

        token, feed_token, user_id, error = authenticate_broker("mock_request_token")

        assert token is None
        assert feed_token is None
        assert user_id is None
        assert "Network error" in error
        mock_httpx_client.post.assert_called_once()
        mock_auth_token_db.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_feed_token_success(self, mock_settings, mock_httpx_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "type": "success",
            "result": {"token": "mock_feed_token_result", "userID": "mock_user_id_result"},
        }
        mock_httpx_client.post.return_value = mock_response

        feed_token, user_id, error = get_feed_token()

        assert feed_token == "mock_feed_token_result"
        assert user_id == "mock_user_id_result"
        assert error is None
        mock_httpx_client.post.assert_called_once()


class TestFivepaisaXTSData:
    @pytest.mark.asyncio
    async def test_get_api_response_get_success(self, mock_httpx_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"type": "success", "data": "test_data"}
        mock_httpx_client.get.return_value = mock_response

        response_data = get_api_response("/test_endpoint", "mock_auth", method="GET")

        assert response_data == {"type": "success", "data": "test_data"}
        mock_httpx_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_api_response_post_success(self, mock_httpx_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"type": "success", "data": "test_data"}
        mock_httpx_client.post.return_value = mock_response

        response_data = get_api_response(
            "/test_endpoint", "mock_auth", method="POST", payload={"key": "value"}
        )

        assert response_data == {"type": "success", "data": "test_data"}
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_api_response_error_response(self, mock_httpx_client):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"type": "error", "message": "Bad Request"}
        mock_httpx_client.get.return_value = mock_response

        with pytest.raises(Exception) as excinfo:
            get_api_response("/test_endpoint", "mock_auth", method="GET")
        assert "API request failed" in str(excinfo.value)
        mock_httpx_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_api_response_network_error(self, mock_httpx_client):
        mock_httpx_client.get.side_effect = Exception("Network is down")

        with pytest.raises(Exception) as excinfo:
            get_api_response("/test_endpoint", "mock_auth", method="GET")
        assert "Network is down" in str(excinfo.value)
        mock_httpx_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_broker_data_get_instrument_token_success(self, mock_get_br_symbol):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_first = MagicMock()

        mock_first.return_value = MagicMock(token="mock_instrument_token")
        mock_filter.return_value.first = mock_first
        mock_query.return_value.filter = mock_filter
        mock_session.query.return_value = mock_query

        with patch(
            "app.web.brokers.fivepaisaxts.api.data.db_session",
            return_value=mock_session,
        ):
            broker_data = BrokerData("mock_auth_token")
            symbol_info, brexchange = broker_data._get_instrument_token("TEST", "NSE")

            assert symbol_info.token == "mock_instrument_token"
            assert brexchange == 1
            mock_get_br_symbol.assert_called_once_with("TEST", "NSE")

    @pytest.mark.asyncio
    async def test_broker_data_get_instrument_token_unknown_exchange(self):
        broker_data = BrokerData("mock_auth_token")
        with pytest.raises(Exception) as excinfo:
            broker_data._get_instrument_token("TEST", "UNKNOWN")
        assert "Unknown exchange segment: UNKNOWN" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_broker_data_get_instrument_token_not_found(
        self, mock_get_br_symbol
    ):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_first = MagicMock()

        mock_first.return_value = None
        mock_filter.return_value.first = mock_first
        mock_query.return_value.filter = mock_filter
        mock_session.query.return_value = mock_query

        with patch(
            "app.web.brokers.fivepaisaxts.api.data.db_session",
            return_value=mock_session,
        ):
            broker_data = BrokerData("mock_auth_token")
            with pytest.raises(Exception) as excinfo:
                broker_data._get_instrument_token("TEST", "NSE")
            assert "Could not find exchange token for NSE:BR_SYMBOL" in str(
                excinfo.value
            )

    @pytest.mark.asyncio
    async def test_broker_data_fetch_market_data_success(self):
        mock_get_api_response = MagicMock()
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"listQuotes": ['{"Touchline": {"LastTradedPrice": 100}}']},
        }

        with patch(
            "app.web.brokers.fivepaisaxts.api.data.get_api_response",
            new=mock_get_api_response,
        ):
            broker_data = BrokerData("mock_auth_token", feed_token="mock_feed_token")
            token = {"exchangeSegment": 1, "exchangeInstrumentID": 12345}
            market_data = broker_data._fetch_market_data(token, 1502)

            assert market_data == {"Touchline": {"LastTradedPrice": 100}}
            mock_get_api_response.assert_called_once()


    @pytest.mark.asyncio
    async def test_broker_data_get_quotes_success(self, mock_get_br_symbol):
        mock_symbol_info = MagicMock(token="mock_instrument_token")
        mock_get_instrument_token = MagicMock(return_value=(mock_symbol_info, 1))
        mock_fetch_market_data = MagicMock(
            side_effect=[
                {"Touchline": {"LastTradedPrice": 100, "Open": 90, "High": 110, "Low": 80, "TotalTradedQuantity": 1000, "AskInfo": {"Price": 101}, "BidInfo": {"Price": 99}, "Close": 95}},
                {"OpenInterest": 500},
            ]
        )

        with patch("app.web.brokers.fivepaisaxts.api.data.BrokerData._get_instrument_token", new=mock_get_instrument_token), \
             patch("app.web.brokers.fivepaisaxts.api.data.BrokerData._fetch_market_data", new=mock_fetch_market_data):
            broker_data = BrokerData("mock_auth_token", feed_token="mock_feed_token")
            quotes = broker_data.get_quotes("TEST", "NSE")

            assert quotes["ltp"] == 100
            assert quotes["open"] == 90
            assert quotes["high"] == 110
            assert quotes["low"] == 80
            assert quotes["volume"] == 1000
            assert quotes["ask"] == 101
            assert quotes["bid"] == 99
            assert quotes["prev_close"] == 95
            assert quotes["oi"] == 500
            mock_get_instrument_token.assert_called_once_with("TEST", "NSE")
            assert mock_fetch_market_data.call_count == 2

    @pytest.mark.asyncio
    async def test_broker_data_get_quotes_no_market_data(self, mock_get_br_symbol):
        mock_symbol_info = MagicMock(token="mock_instrument_token")
        mock_get_instrument_token = MagicMock(return_value=(mock_symbol_info, 1))
        mock_fetch_market_data = MagicMock(return_value=None)

        with patch("app.web.brokers.fivepaisaxts.api.data.BrokerData._get_instrument_token", new=mock_get_instrument_token), \
             patch("app.web.brokers.fivepaisaxts.api.data.BrokerData._fetch_market_data", new=mock_fetch_market_data):
            broker_data = BrokerData("mock_auth_token", feed_token="mock_feed_token")
            with pytest.raises(Exception) as excinfo:
                broker_data.get_quotes("TEST", "NSE")
            assert "Failed to fetch market data" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_broker_data_get_quotes_exception(self, mock_get_br_symbol):
        mock_get_instrument_token = MagicMock(side_effect=Exception("Token error"))

        with patch("app.web.brokers.fivepaisaxts.api.data.BrokerData._get_instrument_token", new=mock_get_instrument_token):
            broker_data = BrokerData("mock_auth_token", feed_token="mock_feed_token")
            with pytest.raises(Exception) as excinfo:
                broker_data.get_quotes("TEST", "NSE")
            assert "Token error" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_broker_data_get_history_success(self, mock_get_br_symbol):
        mock_symbol_info = MagicMock(token="mock_instrument_token")
        mock_db_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_symbol_info

        mock_get_api_response = MagicMock(
            return_value={
                "type": "success",
                "result": {"dataReponse": "1672531200|100|110|90|105|1000,1672617600|105|115|95|110|1200"},
            }
        )

        with patch("app.web.brokers.fivepaisaxts.api.data.db_session", new=mock_db_session), \
             patch("app.web.brokers.fivepaisaxts.api.data.get_api_response", new=mock_get_api_response):
            broker_data = BrokerData("mock_auth_token", feed_token="mock_feed_token")
            df = broker_data.get_history("TEST", "NSE", "1D", "2023-01-01", "2023-01-02")

            assert not df.empty
            assert len(df) == 2
            assert df["open"].iloc[0] == 100
            assert df["close"].iloc[1] == 110
            mock_get_api_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_broker_data_get_history_no_data_response(self, mock_get_br_symbol):
        mock_symbol_info = MagicMock(token="mock_instrument_token")
        mock_db_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_symbol_info

        mock_get_api_response = MagicMock(
            return_value={"type": "success", "result": {"dataReponse": ""}}
        )

        with patch("app.web.brokers.fivepaisaxts.api.data.db_session", new=mock_db_session), \
             patch("app.web.brokers.fivepaisaxts.api.data.get_api_response", new=mock_get_api_response):
            broker_data = BrokerData("mock_auth_token", feed_token="mock_feed_token")
            df = broker_data.get_history("TEST", "NSE", "1D", "2023-01-01", "2023-01-02")
            assert df.empty
            mock_get_api_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_broker_data_get_history_unsupported_timeframe(self):
        broker_data = BrokerData("mock_auth_token")
        with pytest.raises(Exception) as excinfo:
            broker_data.get_history("TEST", "NSE", "UNKNOWN", "2023-01-01", "2023-01-02")
        assert "Unsupported timeframe: UNKNOWN" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_broker_data_get_history_exception(self, mock_get_br_symbol):
        mock_get_br_symbol.side_effect = Exception("Symbol error")
        broker_data = BrokerData("mock_auth_token")
        with pytest.raises(Exception) as excinfo:
            broker_data.get_history("TEST", "NSE", "1D", "2023-01-01", "2023-01-02")
        assert "Symbol error" in str(excinfo.value)

    def test_broker_data_get_intervals(self):
        broker_data = BrokerData("mock_auth_token")
        intervals = broker_data.get_intervals()
        assert isinstance(intervals, list)
        assert "1m" in intervals
        assert "D" in intervals

    @pytest.mark.asyncio
    async def test_broker_data_get_market_depth_success(self, mock_get_br_symbol):
        mock_symbol_info = MagicMock(token="mock_instrument_token")
        mock_db_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_symbol_info

        mock_fetch_market_data = MagicMock(
            side_effect=[
                {
                    "Touchline": {
                        "LastTradedPrice": 100, "Open": 90, "High": 110, "Low": 80,
                        "TotalTradedQuantity": 1000, "Close": 95, "TotalBuyQuantity": 500, "TotalSellQuantity": 400
                    },
                    "Bids": [{"Price": 99, "Size": 100}],
                    "Asks": [{"Price": 101, "Size": 150}],
                },
                {"OpenInterest": 500},
            ]
        )

        with patch("app.web.brokers.fivepaisaxts.api.data.db_session", new=mock_db_session), \
             patch("app.web.brokers.fivepaisaxts.api.data.BrokerData._fetch_market_data", new=mock_fetch_market_data), \
             patch("app.web.brokers.fivepaisaxts.api.data.get_feed_token", return_value=("mock_feed_token", "mock_user_id", None)):

            broker_data = BrokerData("mock_auth_token", user_id="mock_user_id")
            depth = broker_data.get_market_depth("TEST", "NSE")

            assert depth["ltp"] == 100
            assert depth["oi"] == 500
            assert depth["bids"][0]["price"] == 99
            assert depth["asks"][0]["price"] == 101
            assert depth["totalbuyqty"] == 500
            assert depth["totalsellqty"] == 400
            assert mock_fetch_market_data.call_count == 2

    @pytest.mark.asyncio
    async def test_broker_data_get_market_depth_no_market_data(self, mock_get_br_symbol):
        mock_symbol_info = MagicMock(token="mock_instrument_token")
        mock_db_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_symbol_info

        mock_fetch_market_data = MagicMock(side_effect=[None, {"OpenInterest": 500}])

        with patch("app.web.brokers.fivepaisaxts.api.data.db_session", new=mock_db_session), \
             patch("app.web.brokers.fivepaisaxts.api.data.BrokerData._fetch_market_data", new=mock_fetch_market_data), \
             patch("app.web.brokers.fivepaisaxts.api.data.get_feed_token", return_value=("mock_feed_token", "mock_user_id", None)):

            broker_data = BrokerData("mock_auth_token", user_id="mock_user_id")
            with pytest.raises(Exception) as excinfo:
                broker_data.get_market_depth("TEST", "NSE")
            assert "Failed to fetch market data" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_broker_data_get_market_depth_exception(self, mock_get_br_symbol):
        mock_get_br_symbol.side_effect = Exception("Depth error")
        broker_data = BrokerData("mock_auth_token")
        with pytest.raises(Exception) as excinfo:
            broker_data.get_market_depth("TEST", "NSE")
        assert "Depth error" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_broker_data_get_depth_alias(self, mock_get_br_symbol):
        mock_symbol_info = MagicMock(token="mock_instrument_token")
        mock_db_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_symbol_info

        mock_fetch_market_data = MagicMock(
            side_effect=[
                {
                    "Touchline": {
                        "LastTradedPrice": 100, "Open": 90, "High": 110, "Low": 80,
                        "TotalTradedQuantity": 1000, "Close": 95, "TotalBuyQuantity": 500, "TotalSellQuantity": 400
                    },
                    "Bids": [{"Price": 99, "Size": 100}],
                    "Asks": [{"Price": 101, "Size": 150}],
                },
                {"OpenInterest": 500},
            ]
        )

        with patch("app.web.brokers.fivepaisaxts.api.data.db_session", new=mock_db_session), \
             patch("app.web.brokers.fivepaisaxts.api.data.BrokerData._fetch_market_data", new=mock_fetch_market_data), \
             patch("app.web.brokers.fivepaisaxts.api.data.get_feed_token", return_value=("mock_feed_token", "mock_user_id", None)):

            broker_data = BrokerData("mock_auth_token", user_id="mock_user_id")
            depth = broker_data.get_depth("TEST", "NSE")

            assert depth["ltp"] == 100
            assert depth["oi"] == 500
            assert depth["bids"][0]["price"] == 99
            assert depth["asks"][0]["price"] == 101
            assert mock_fetch_market_data.call_count == 2


class TestFivepaisaXTSOrder:
    @pytest.mark.asyncio
    async def test_get_order_book_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {"type": "success", "result": [{"AppOrderID": "123"}]}
        order_book = get_order_book("mock_auth")
        assert order_book["type"] == "success"
        assert order_book["result"][0]["AppOrderID"] == "123"

    @pytest.mark.asyncio
    async def test_get_order_book_failure(self, mock_get_api_response):
        mock_get_api_response.return_value = {"type": "error", "message": "Failed"}
        order_book = get_order_book("mock_auth")
        assert order_book["type"] == "error"

    @pytest.mark.asyncio
    async def test_get_trade_book_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {"type": "success", "result": [{"TradeID": "456"}]}
        trade_book = get_trade_book("mock_auth")
        assert trade_book["type"] == "success"
        assert trade_book["result"][0]["TradeID"] == "456"

    @pytest.mark.asyncio
    async def test_get_trade_book_failure(self, mock_get_api_response):
        mock_get_api_response.return_value = {"type": "error", "message": "Failed"}
        trade_book = get_trade_book("mock_auth")
        assert trade_book["type"] == "error"

    @pytest.mark.asyncio
    async def test_get_positions_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {"type": "success", "result": {"positionList": [{"Symbol": "TEST"}]}}
        positions = get_positions("mock_auth")
        assert positions["type"] == "success"
        assert positions["result"]["positionList"][0]["Symbol"] == "TEST"

    @pytest.mark.asyncio
    async def test_get_positions_failure(self, mock_get_api_response):
        mock_get_api_response.return_value = {"type": "error", "message": "Failed"}
        positions = get_positions("mock_auth")
        assert positions["type"] == "error"

    @pytest.mark.asyncio
    async def test_get_holdings_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {"type": "success", "result": {"holdingList": [{"Symbol": "HDFC"}]}}
        holdings = get_holdings("mock_auth")
        assert holdings["type"] == "success"
        assert holdings["result"]["holdingList"][0]["Symbol"] == "HDFC"

    @pytest.mark.asyncio
    async def test_get_holdings_failure(self, mock_get_api_response):
        mock_get_api_response.return_value = {"type": "error", "message": "Failed"}
        holdings = get_holdings("mock_auth")
        assert holdings["type"] == "error"

    @pytest.mark.asyncio
    async def test_get_open_position_success(self, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "TESTBR"
        with patch("app.web.brokers.fivepaisaxts.api.order_api.get_positions") as mock_get_positions:
            mock_get_positions.return_value = {
                "status": True,
                "data": [
                    {"tradingsymbol": "TESTBR", "exchange": "NSE", "producttype": "CNC", "Quantity": "10"}
                ]
            }
            net_qty = get_open_position("TEST", "NSE", "CNC", "mock_auth")
            assert net_qty == "10"

    @pytest.mark.asyncio
    async def test_get_open_position_no_match(self, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "NOMATCH"
        with patch("app.web.brokers.fivepaisaxts.api.order_api.get_positions") as mock_get_positions:
            mock_get_positions.return_value = {
                "status": True,
                "data": [
                    {"tradingsymbol": "TESTBR", "exchange": "NSE", "producttype": "CNC", "Quantity": "10"}
                ]
            }
            net_qty = get_open_position("TEST", "NSE", "CNC", "mock_auth")
            assert net_qty == "0"

    @pytest.mark.asyncio
    async def test_place_order_api_success(self, mock_httpx_client):
        mock_httpx_client.post.return_value.status_code = 200
        mock_httpx_client.post.return_value.json.return_value = {"type": "success", "result": {"AppOrderID": "ORDER123"}}
        mock_httpx_client.post.return_value.text = '{"type": "success", "result": {"AppOrderID": "ORDER123"}}'

        with patch("app.web.brokers.fivepaisaxts.api.order_api.get_token", return_value="mock_token"), \
             patch("app.web.brokers.fivepaisaxts.api.order_api.transform_data", return_value={"transformed": "data"}):
            data = {"symbol": "TEST", "exchange": "NSE", "productType": "CNC", "orderType": "MARKET"}
            response, response_data, orderid = place_order_api(data, "mock_auth")

            assert response.status_code == 200
            assert response_data["type"] == "success"
            assert orderid == "ORDER123"
            mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_place_order_api_direct_instrument_id_payload(self, mock_httpx_client):
        mock_httpx_client.post.return_value.status_code = 200
        mock_httpx_client.post.return_value.json.return_value = {"type": "success", "result": {"AppOrderID": "ORDER456"}}
        mock_httpx_client.post.return_value.text = '{"type": "success", "result": {"AppOrderID": "ORDER456"}}'

        data = {"exchangeSegment": "NSE", "exchangeInstrumentID": "12345", "productType": "CNC", "orderType": "MARKET"}
        response, response_data, orderid = place_order_api(data, "mock_auth")

        assert response.status_code == 200
        assert response_data["type"] == "success"
        assert orderid == "ORDER456"
        mock_httpx_client.post.assert_called_once()
        assert mock_httpx_client.post.call_args[1]["json"] == data


    @pytest.mark.asyncio
    async def test_place_order_api_failure(self, mock_httpx_client):
        mock_httpx_client.post.return_value.status_code = 400
        mock_httpx_client.post.return_value.json.return_value = {"type": "error", "message": "Invalid order"}
        mock_httpx_client.post.return_value.text = '{"type": "error", "message": "Invalid order"}'

        with patch("app.web.brokers.fivepaisaxts.api.order_api.get_token", return_value="mock_token"), \
             patch("app.web.brokers.fivepaisaxts.api.order_api.transform_data", return_value={"transformed": "data"}):
            data = {"symbol": "TEST", "exchange": "NSE", "productType": "CNC", "orderType": "MARKET"}
            response, response_data, orderid = place_order_api(data, "mock_auth")

            assert response.status_code == 400
            assert response_data["type"] == "error"
            assert orderid is None

    @pytest.mark.asyncio
    async def test_place_smartorder_api_no_position_no_quantity(self):
        with patch("app.web.brokers.fivepaisaxts.api.order_api.get_open_position", return_value="0"), \
             patch("app.web.brokers.fivepaisaxts.api.order_api.place_order_api") as mock_place_order_api:
            data = {"symbol": "TEST", "exchange": "NSE", "product": "CNC", "position_size": 0, "quantity": "0"}
            res, response, orderid = place_smartorder_api(data, "mock_auth")
            assert res is None
            assert response["message"] == "No action needed. Position size matches current position"
            assert orderid is None
            mock_place_order_api.assert_not_called()

    @pytest.mark.asyncio
    async def test_place_smartorder_api_no_position_with_quantity(self):
        with patch("app.web.brokers.fivepaisaxts.api.order_api.get_open_position", return_value="0"), \
             patch("app.web.brokers.fivepaisaxts.api.order_api.place_order_api", return_value=("res", {"type": "success"}, "id")) as mock_place_order_api:
            data = {"symbol": "TEST", "exchange": "NSE", "product": "CNC", "position_size": 0, "quantity": "10", "action": "BUY"}
            res, response, orderid = place_smartorder_api(data, "mock_auth")
            assert res == "res"
            assert response["type"] == "success"
            assert orderid == "id"
            mock_place_order_api.assert_called_once()

    @pytest.mark.asyncio
    async def test_place_smartorder_api_square_off_positive_position(self):
        with patch("app.web.brokers.fivepaisaxts.api.order_api.get_open_position", return_value="10"), \
             patch("app.web.brokers.fivepaisaxts.api.order_api.place_order_api", return_value=("res", {"type": "success"}, "id")) as mock_place_order_api:
            data = {"symbol": "TEST", "exchange": "NSE", "product": "CNC", "position_size": 0, "quantity": "0"}
            res, response, orderid = place_smartorder_api(data, "mock_auth")
            assert res == "res"
            assert response["type"] == "success"
            assert orderid == "id"
            mock_place_order_api.assert_called_once()
            assert mock_place_order_api.call_args[0][0]["action"] == "SELL"
            assert mock_place_order_api.call_args[0][0]["quantity"] == "10"

    @pytest.mark.asyncio
    async def test_place_smartorder_api_square_off_negative_position(self):
        with patch("app.web.brokers.fivepaisaxts.api.order_api.get_open_position", return_value="-10"), \
             patch("app.web.brokers.fivepaisaxts.api.order_api.place_order_api", return_value=("res", {"type": "success"}, "id")) as mock_place_order_api:
            data = {"symbol": "TEST", "exchange": "NSE", "product": "CNC", "position_size": 0, "quantity": "0"}
            res, response, orderid = place_smartorder_api(data, "mock_auth")
            assert res == "res"
            assert response["type"] == "success"
            assert orderid == "id"
            mock_place_order_api.assert_called_once()
            assert mock_place_order_api.call_args[0][0]["action"] == "BUY"
            assert mock_place_order_api.call_args[0][0]["quantity"] == "10"

    @pytest.mark.asyncio
    async def test_place_smartorder_api_increase_positive_position(self):
        with patch("app.web.brokers.fivepaisaxts.api.order_api.get_open_position", return_value="5"), \
             patch("app.web.brokers.fivepaisaxts.api.order_api.place_order_api", return_value=("res", {"type": "success"}, "id")) as mock_place_order_api:
            data = {"symbol": "TEST", "exchange": "NSE", "product": "CNC", "position_size": 15, "quantity": "0"}
            res, response, orderid = place_smartorder_api(data, "mock_auth")
            assert res == "res"
            assert response["type"] == "success"
            assert orderid == "id"
            mock_place_order_api.assert_called_once()
            assert mock_place_order_api.call_args[0][0]["action"] == "BUY"
            assert mock_place_order_api.call_args[0][0]["quantity"] == "10"

    @pytest.mark.asyncio
    async def test_place_smartorder_api_reduce_positive_position(self):
        with patch("app.web.brokers.fivepaisaxts.api.order_api.get_open_position", return_value="15"), \
             patch("app.web.brokers.fivepaisaxts.api.order_api.place_order_api", return_value=("res", {"type": "success"}, "id")) as mock_place_order_api:
            data = {"symbol": "TEST", "exchange": "NSE", "product": "CNC", "position_size": 5, "quantity": "0"}
            res, response, orderid = place_smartorder_api(data, "mock_auth")
            assert res == "res"
            assert response["type"] == "success"
            assert orderid == "id"
            mock_place_order_api.assert_called_once()
            assert mock_place_order_api.call_args[0][0]["action"] == "SELL"
            assert mock_place_order_api.call_args[0][0]["quantity"] == "10"

    @pytest.mark.asyncio
    async def test_close_all_positions_no_open_positions(self):
        with patch("app.web.brokers.fivepaisaxts.api.order_api.get_positions", return_value={"type": "success", "result": {"positionList": []}}):
            response, status = close_all_positions("mock_api_key", "mock_auth")
            assert response["message"] == "No Open Positions Found"
            assert status == 200

    @pytest.mark.asyncio
    async def test_close_all_positions_success(self):
        mock_positions = {
            "type": "success",
            "result": {
                "positionList": [
                    {"Quantity": "10", "ExchangeSegment": "NSE", "ExchangeInstrumentId": "123", "ProductType": "CNC"},
                    {"Quantity": "-5", "ExchangeSegment": "BSE", "ExchangeInstrumentId": "456", "ProductType": "MIS"},
                ]
            }
        }
        with patch("app.web.brokers.fivepaisaxts.api.order_api.get_positions", return_value=mock_positions), \
             patch("app.web.brokers.fivepaisaxts.api.order_api.place_order_api", return_value=("res", {"type": "success"}, "id")) as mock_place_order_api:
            response, status = close_all_positions("mock_api_key", "mock_auth")
            assert response["message"] == "All Open Positions SquaredOff"
            assert status == 200
            assert mock_place_order_api.call_count == 2
            # Check the first call (SELL 10)
            assert mock_place_order_api.call_args_list[0][0][0]["orderSide"] == "SELL"
            assert mock_place_order_api.call_args_list[0][0][0]["orderQuantity"] == "10"
            # Check the second call (BUY 5)
            assert mock_place_order_api.call_args_list[1][0][0]["orderSide"] == "BUY"
            assert mock_place_order_api.call_args_list[1][0][0]["orderQuantity"] == "5"

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, mock_httpx_client):
        mock_httpx_client.delete.return_value.status_code = 200
        mock_httpx_client.delete.return_value.text = '{"status": true, "message": "Order cancelled"}'
        response, status = cancel_order("ORDER123", "mock_auth")
        assert response["status"] == "success"
        assert response["orderid"] == "ORDER123"
        assert status == 200
        mock_httpx_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_order_failure(self, mock_httpx_client):
        mock_httpx_client.delete.return_value.status_code = 400
        mock_httpx_client.delete.return_value.text = '{"status": false, "message": "Failed to cancel"}'
        response, status = cancel_order("ORDER123", "mock_auth")
        assert response["status"] == "error"
        assert status == 400

    @pytest.mark.asyncio
    async def test_modify_order_success(self, mock_httpx_client):
        mock_httpx_client.put.return_value.status_code = 200
        mock_httpx_client.put.return_value.text = '{"status": "true", "data": {"orderid": "MODIFIED123"}}'

        with patch("app.web.brokers.fivepaisaxts.api.order_api.get_token", return_value="mock_token"), \
             patch("app.web.brokers.fivepaisaxts.api.order_api.get_br_symbol", return_value="TESTBR"), \
             patch("app.web.brokers.fivepaisaxts.api.order_api.transform_modify_order_data", return_value={"modified": "data"}):
            data = {"symbol": "TEST", "exchange": "NSE"}
            response, status = modify_order(data, "mock_auth")
            assert response["status"] == "success"
            assert response["orderid"] == "MODIFIED123"
            assert status == 200
            mock_httpx_client.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_modify_order_failure(self, mock_httpx_client):
        mock_httpx_client.put.return_value.status_code = 400
        mock_httpx_client.put.return_value.text = '{"status": "false", "message": "Failed to modify"}'

        with patch("app.web.brokers.fivepaisaxts.api.order_api.get_token", return_value="mock_token"), \
             patch("app.web.brokers.fivepaisaxts.api.order_api.get_br_symbol", return_value="TESTBR"), \
             patch("app.web.brokers.fivepaisaxts.api.order_api.transform_modify_order_data", return_value={"modified": "data"}):
            data = {"symbol": "TEST", "exchange": "NSE"}
            response, status = modify_order(data, "mock_auth")
            assert response["status"] == "error"
            assert status == 400

    @pytest.mark.asyncio
    async def test_cancel_all_orders_api_success(self):
        mock_order_book = {
            "type": "success",
            "result": [
                {"AppOrderID": "1", "OrderStatus": "New"},
                {"AppOrderID": "2", "OrderStatus": "Trigger Pending"},
                {"AppOrderID": "3", "OrderStatus": "Filled"},
            ]
        }
        with patch("app.web.brokers.fivepaisaxts.api.order_api.get_order_book", return_value=mock_order_book), \
             patch("app.web.brokers.fivepaisaxts.api.order_api.cancel_order", side_effect=[
                 ({"status": "success", "orderid": "1"}, 200),
                 ({"status": "success", "orderid": "2"}, 200),
             ]) as mock_cancel_order:
            canceled, failed = cancel_all_orders_api({}, "mock_auth")
            assert canceled == ["1", "2"]
            assert failed == []
            assert mock_cancel_order.call_count == 2

    @pytest.mark.asyncio
    async def test_cancel_all_orders_api_partial_failure(self):
        mock_order_book = {
            "type": "success",
            "result": [
                {"AppOrderID": "1", "OrderStatus": "New"},
                {"AppOrderID": "2", "OrderStatus": "Trigger Pending"},
            ]
        }
        with patch("app.web.brokers.fivepaisaxts.api.order_api.get_order_book", return_value=mock_order_book), \
             patch("app.web.brokers.fivepaisaxts.api.order_api.cancel_order", side_effect=[
                 ({"status": "success", "orderid": "1"}, 200),
                 ({"status": "error", "message": "failed"}, 400),
             ]) as mock_cancel_order:
            canceled, failed = cancel_all_orders_api({}, "mock_auth")
            assert canceled == ["1"]
            assert failed == ["2"]
            assert mock_cancel_order.call_count == 2

    @pytest.mark.asyncio
    async def test_cancel_all_orders_api_no_open_orders(self):
        mock_order_book = {
            "type": "success",
            "result": [
                {"AppOrderID": "3", "OrderStatus": "Filled"},
            ]
        }
        with patch("app.web.brokers.fivepaisaxts.api.order_api.get_order_book", return_value=mock_order_book), \
             patch("app.web.brokers.fivepaisaxts.api.order_api.cancel_order") as mock_cancel_order:
            canceled, failed = cancel_all_orders_api({}, "mock_auth")
            assert canceled == []
            assert failed == []
            mock_cancel_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_all_orders_api_get_order_book_failure(self):
        with patch("app.web.brokers.fivepaisaxts.api.order_api.get_order_book", return_value={"type": "error"}), \
             patch("app.web.brokers.fivepaisaxts.api.order_api.cancel_order") as mock_cancel_order:
            canceled, failed = cancel_all_orders_api({}, "mock_auth")
            assert canceled == []
            assert failed == []
            mock_cancel_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_broker_data_fetch_market_data_api_error(self):
        mock_get_api_response = MagicMock()
        mock_get_api_response.return_value = {
            "type": "error",
            "description": "API Error",
        }

        with patch(
            "app.web.brokers.fivepaisaxts.api.data.get_api_response",
            new=mock_get_api_response,
        ):
            broker_data = BrokerData("mock_auth_token", feed_token="mock_feed_token")
            token = {"exchangeSegment": 1, "exchangeInstrumentID": 12345}
            market_data = broker_data._fetch_market_data(token, 1502)

            assert market_data is None
            mock_get_api_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_broker_data_fetch_market_data_empty_list_quotes(self):
        mock_get_api_response = MagicMock()
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"listQuotes": []},
        }

        with patch(
            "app.web.brokers.fivepaisaxts.api.data.get_api_response",
            new=mock_get_api_response,
        ):
            broker_data = BrokerData("mock_auth_token", feed_token="mock_feed_token")
            token = {"exchangeSegment": 1, "exchangeInstrumentID": 12345}
            market_data = broker_data._fetch_market_data(token, 1502)

            assert market_data is None
            mock_get_api_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_broker_data_fetch_market_data_exception(self):
        mock_get_api_response = MagicMock(side_effect=Exception("Data fetch error"))

        with patch(
            "app.web.brokers.fivepaisaxts.api.data.get_api_response",
            new=mock_get_api_response,
        ):
            broker_data = BrokerData("mock_auth_token", feed_token="mock_feed_token")
            token = {"exchangeSegment": 1, "exchangeInstrumentID": 12345}
            market_data = broker_data._fetch_market_data(token, 1502)

            assert market_data is None
            mock_get_api_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_feed_token_api_error(self, mock_settings, mock_httpx_client):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"description": "Feed API error"}
        mock_httpx_client.post.return_value = mock_response

        feed_token, user_id, error = get_feed_token()

        assert feed_token is None
        assert user_id is None
        assert "Feed API error" in error
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_feed_token_exception(self, mock_settings, mock_httpx_client):
        mock_httpx_client.post.side_effect = Exception("Feed network error")

        feed_token, user_id, error = get_feed_token()

        assert feed_token is None
        assert user_id is None
        assert "Feed network error" in error
        mock_httpx_client.post.assert_called_once()
