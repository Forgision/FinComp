import pytest
pytest.skip("Skipped by user request", allow_module_level=True)
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json
from datetime import datetime
from pytz import timezone
from unittest.mock import ANY

from app.web.brokers.indmoney.api.auth_api import authenticate_broker
from app.web.brokers.indmoney.api.data import BrokerData, get_api_response as get_data_api_response
from app.web.brokers.indmoney.api.funds import get_margin_data, DEFAULT_MARGIN_RESPONSE
from app.web.brokers.indmoney.api.order_api import (
    get_api_response as get_order_api_response,
    get_positions
)

IST = timezone('Asia/Kolkata')


# Fixtures for common mocks
@pytest.fixture
def mock_settings():
    with patch('app.core.config.settings') as mock:
        mock.BROKER_API_SECRET = "test_secret"
        mock.BROKER_API_KEY = "test_api_key"
        yield mock

@pytest.fixture
def mock_logger():
    with patch('app.utils.logging.logger') as mock:
        yield mock

@pytest.fixture
def mock_httpx_client():
    with patch('app.utils.httpx_client.get_httpx_client') as mock:
        mock_client = AsyncMock()
        mock.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_get_url():
    with patch('app.web.broker.broker.indmoney.api.baseurl.get_url') as mock:
        mock.side_effect = lambda endpoint: f"https://api.indmoney.com{endpoint}"
        yield mock

@pytest.fixture
def mock_get_token():
    with patch('app.core.schemas.token_db.get_token') as mock:
        mock.return_value = "12345"
        yield mock

@pytest.fixture
def mock_get_br_symbol():
    with patch('app.core.schemas.token_db.get_br_symbol') as mock:
        mock.return_value = "BR_SYMBOL"
        yield mock

@pytest.fixture
def mock_get_symbol():
    with patch('app.core.schemas.token_db.get_symbol') as mock:
        mock.return_value = "OPENALGO_SYMBOL"
        yield mock

@pytest.fixture
def mock_transform_data():
    with patch('app.web.broker.broker.indmoney.mapping.transform_data.transform_data') as mock:
        mock.return_value = {"transformed": "data"}
        yield mock

@pytest.fixture
def mock_transform_modify_order_data():
    with patch('app.web.broker.broker.indmoney.mapping.transform_data.transform_modify_order_data') as mock:
        mock.return_value = {"transformed_modify": "data"}
        yield mock

@pytest.fixture
def mock_map_exchange_type():
    with patch('app.web.broker.broker.indmoney.mapping.transform_data.map_exchange_type') as mock:
        mock.return_value = "NSE"
        yield mock

@pytest.fixture
def mock_map_product_type():
    with patch('app.web.broker.broker.indmoney.mapping.transform_data.map_product_type') as mock:
        mock.return_value = "MIS"
        yield mock


class TestIndmoneyAuth:
    @patch('app.web.broker.broker.indmoney.api.auth_api.settings')
    def test_authenticate_broker_success(self, mock_settings):
        mock_settings.BROKER_API_SECRET = "test_access_token"
        token, error = authenticate_broker("some_code")
        assert token == "test_access_token"
        assert error is None

    @patch('app.web.broker.broker.indmoney.api.auth_api.settings')
    def test_authenticate_broker_no_secret(self, mock_settings):
        mock_settings.BROKER_API_SECRET = None
        token, error = authenticate_broker("some_code")
        assert token is None
        assert "No access token found" in error



class TestIndmoneyData:
    @pytest.mark.asyncio
    @patch('app.web.broker.broker.indmoney.api.data.get_url')
    @patch('app.web.broker.broker.indmoney.api.data.get_httpx_client')
    @patch('app.web.broker.broker.indmoney.api.data.logger')
    async def test_get_api_response_success(self, mock_logger, mock_get_httpx_client, mock_get_url, mock_settings):
        mock_settings.INDMONEY_MARKETDATA_URL = "http://testurl.com"
        mock_get_url.return_value = "http://testurl.com/test_path"
        mock_client = AsyncMock()
        mock_get_httpx_client.return_value = mock_client
        expected_response_data = {"data": "test"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_response_data
        mock_response.text = json.dumps(expected_response_data)
        mock_client.get.return_value = mock_response

        response_data, error = await get_data_api_response("test_path", "test_token", "marketdata")
        assert response_data == expected_response_data
        assert error is None
        mock_get_url.assert_called_once_with("test_path")
        mock_client.get.assert_called_once_with(
            "http://testurl.com/test_path", headers={'Authorization': 'test_token', 'Content-Type': 'application/json', 'Accept': 'application/json'}, params=None
        )

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.indmoney.api.data.get_url')
    @patch('app.web.broker.broker.indmoney.api.data.get_httpx_client')
    @patch('app.web.broker.broker.indmoney.api.data.logger')
    async def test_get_api_response_http_error(self, mock_logger, mock_get_httpx_client, mock_get_url, mock_settings):
        mock_settings.INDMONEY_MARKETDATA_URL = "http://testurl.com"
        mock_get_url.return_value = "http://testurl.com/test_path"
        mock_client = AsyncMock()
        mock_get_httpx_client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_client.get.return_value = mock_response

        response_data, error = await get_data_api_response("test_path", "test_token", "marketdata")
        assert response_data is None
        assert "HTTP Error 400: Bad Request" in error
        mock_get_url.assert_called_once_with("test_path")
        mock_client.get.assert_called_once_with(
            "http://testurl.com/test_path", headers={'Authorization': 'test_token', 'Content-Type': 'application/json', 'Accept': 'application/json'}, params=None
        )
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.indmoney.api.data.get_url')
    @patch('app.web.broker.broker.indmoney.api.data.get_httpx_client')
    @patch('app.web.broker.broker.indmoney.api.data.logger')
    async def test_get_api_response_json_decode_error(self, mock_logger, mock_get_httpx_client, mock_get_url, mock_settings):
        mock_settings.INDMONEY_MARKETDATA_URL = "http://testurl.com"
        mock_get_url.return_value = "http://testurl.com/test_path"
        mock_client = AsyncMock()
        mock_get_httpx_client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
        mock_response.text = "Invalid JSON"
        mock_client.get.return_value = mock_response

        response_data, error = await get_data_api_response("test_path", "test_token", "marketdata")
        assert response_data is None
        assert "JSONDecodeError: Invalid JSON" in error
        mock_get_url.assert_called_once_with("test_path")
        mock_client.get.assert_called_once_with(
            "http://testurl.com/test_path", headers={'Authorization': 'test_token', 'Content-Type': 'application/json', 'Accept': 'application/json'}, params=None
        )
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.indmoney.api.data.get_url')
    @patch('app.web.broker.broker.indmoney.api.data.get_httpx_client')
    @patch('app.web.broker.broker.indmoney.api.data.logger')
    async def test_get_api_response_exception(self, mock_logger, mock_get_httpx_client, mock_get_url, mock_settings):
        mock_settings.INDMONEY_MARKETDATA_URL = "http://testurl.com"
        mock_get_url.return_value = "http://testurl.com/test_path"
        mock_client = AsyncMock()
        mock_get_httpx_client.return_value = mock_client
        mock_client.get.side_effect = Exception("Network Error")

        response_data, error = await get_data_api_response("test_path", "test_token", "marketdata")
        assert response_data is None
        assert "Exception: Network Error" in error
        mock_get_url.assert_called_once_with("test_path")
        mock_client.get.assert_called_once_with(
            "http://testurl.com/test_path", headers={'Authorization': 'test_token', 'Content-Type': 'application/json', 'Accept': 'application/json'}, params=None
        )
        mock_logger.exception.assert_called_once()


    @pytest.mark.asyncio
    @patch('app.web.broker.broker.indmoney.api.data.get_data_api_response')
    async def test_get_scrip_code_success(self, mock_get_data_api_response, mock_settings):
        mock_settings.INDMONEY_MARKETDATA_URL = "http://testurl.com"
        mock_get_data_api_response.return_value = (
            {"data": [{"exchange": "NSE", "securityId": "12345", "symbol": "TEST"}]}, None
        )
        broker_data = BrokerData("test_token")
        scrip_code, error = await broker_data._get_scrip_code("TEST", "NSE")
        assert scrip_code == "12345"
        assert error is None
        mock_get_data_api_response.assert_called_once_with(
            "/v1/market/search?query=TEST", "test_token", "marketdata"
        )

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.indmoney.api.data.get_data_api_response')
    async def test_get_scrip_code_unsupported_exchange(self, mock_get_data_api_response, mock_settings):
        mock_settings.INDMONEY_MARKETDATA_URL = "http://testurl.com"
        mock_get_data_api_response.return_value = (
            {"data": [{"exchange": "BSE", "securityId": "12345", "symbol": "TEST"}]}, None
        )
        broker_data = BrokerData("test_token")
        scrip_code, error = await broker_data._get_scrip_code("TEST", "UNSUPPORTED")
        assert scrip_code is None
        assert "Unsupported exchange: UNSUPPORTED" in error
        mock_get_data_api_response.assert_called_once_with(
            "/v1/market/search?query=TEST", "test_token", "marketdata"
        )

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.indmoney.api.data.get_data_api_response')
    async def test_get_scrip_code_no_security_id(self, mock_get_data_api_response, mock_settings):
        mock_settings.INDMONEY_MARKETDATA_URL = "http://testurl.com"
        mock_get_data_api_response.return_value = ({"data": []}, None)
        broker_data = BrokerData("test_token")
        scrip_code, error = await broker_data._get_scrip_code("TEST", "NSE")
        assert scrip_code is None
        assert "No securityId found for TEST on NSE" in error
        mock_get_data_api_response.assert_called_once_with(
            "/v1/market/search?query=TEST", "test_token", "marketdata"
        )


    @pytest.mark.parametrize("input_value, expected_output", [
        ("123.45", 123.45),
        ("1,234.56", 1234.56),
        ("123", 123.0),
        ("-100", -100.0),
        ("N/A", 0.0),
        ("", 0.0),
        (None, 0.0),
        (123.45, 123.45),
        (123, 123.0),
    ])
    def test_clean_number(self, input_value, expected_output):
        broker_data = BrokerData("test_token")
        result = broker_data._clean_number(input_value)
        assert result == expected_output

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.indmoney.api.data.get_data_api_response')
    @patch('app.web.broker.broker.indmoney.api.data.BrokerData._get_scrip_code')
    async def test_get_depth_success(self, mock_get_scrip_code, mock_get_data_api_response, mock_settings):
        mock_settings.INDMONEY_MARKETDATA_URL = "http://testurl.com"
        mock_get_scrip_code.return_value = ("12345", None)
        mock_get_data_api_response.return_value = (
            {"data": [{"bid": 100.0, "ask": 101.0, "bidQty": 10, "askQty": 20}]}, None
        )
        broker_data = BrokerData("test_token")
        depth, error = await broker_data.get_depth("TEST", "NSE")
        assert depth == {
            "symbol": "TEST",
            "exchange": "NSE",
            "bid": 100.0,
            "ask": 101.0,
            "bidQty": 10,
            "askQty": 20,
        }
        assert error is None
        mock_get_scrip_code.assert_called_once_with("TEST", "NSE")
        mock_get_data_api_response.assert_called_once_with(
            "/v1/market/depth?securityId=12345", "test_token", "marketdata"
        )

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.indmoney.api.data.get_data_api_response')
    @patch('app.web.broker.broker.indmoney.api.data.BrokerData._get_scrip_code')
    async def test_get_depth_empty_response(self, mock_get_scrip_code, mock_get_data_api_response, mock_settings):
        mock_settings.INDMONEY_MARKETDATA_URL = "http://testurl.com"
        mock_get_scrip_code.return_value = ("12345", None)
        mock_get_data_api_response.return_value = ({"data": []}, None)
        broker_data = BrokerData("test_token")
        depth, error = await broker_data.get_depth("TEST", "NSE")
        assert depth == {
            "symbol": "TEST",
            "exchange": "NSE",
            "bid": 0.0,
            "ask": 0.0,
            "bidQty": 0,
            "askQty": 0,
        }
        assert error is None

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.indmoney.api.data.get_data_api_response')
    @patch('app.web.broker.broker.indmoney.api.data.BrokerData._get_scrip_code')
    async def test_get_depth_api_error(self, mock_get_scrip_code, mock_get_data_api_response, mock_settings):
        mock_settings.INDMONEY_MARKETDATA_URL = "http://testurl.com"
        mock_get_scrip_code.return_value = ("12345", None)
        mock_get_data_api_response.return_value = (None, "API Error")
        broker_data = BrokerData("test_token")
        depth, error = await broker_data.get_depth("TEST", "NSE")
        assert depth is None
        assert error == "API Error"

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.indmoney.api.data.BrokerData._get_scrip_code')
    async def test_get_depth_get_scrip_code_error(self, mock_get_scrip_code, mock_settings):
        mock_settings.INDMONEY_MARKETDATA_URL = "http://testurl.com"
        mock_get_scrip_code.return_value = (None, "Scrip Code Error")
        broker_data = BrokerData("test_token")
        depth, error = await broker_data.get_depth("TEST", "NSE")
        assert depth is None
        assert error == "Scrip Code Error"

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.indmoney.api.data.get_api_response')
    @patch('app.web.broker.broker.indmoney.api.data.BrokerData._get_scrip_code')
    @patch('app.web.broker.broker.indmoney.api.data.BrokerData._date_to_timestamp_ms')
    @patch('app.web.broker.broker.indmoney.api.data.BrokerData._split_date_range')
    @patch('app.utils.logging.logger')
    async def test_get_history_success(self, mock_logger, mock_split_date_range, mock_date_to_timestamp_ms, mock_get_scrip_code, mock_get_api_response, mock_settings):
        mock_settings.INDMONEY_MARKETDATA_URL = "http://testurl.com"
        mock_get_scrip_code.return_value = "NSE_12345"
        mock_date_to_timestamp_ms.side_effect = [1672531200000, 1672617599000, 1672531200000, 1672617599000] # Jan 1, 2023 to Jan 1, 2023
        mock_split_date_range.return_value = [("2023-01-01", "2023-01-01")]
        mock_get_api_response.return_value = {
            "status": "success",
            "data": [
                {"ts": 1672531200, "o": 100, "h": 105, "l": 98, "c": 103, "v": 1000},
                {"ts": 1672534800, "o": 103, "h": 108, "l": 101, "c": 106, "v": 1200}
            ]
        }

        broker_data = BrokerData("test_auth_token")
        df = await broker_data.get_history("RELIANCE", "NSE", "1h", "2023-01-01", "2023-01-01")

        mock_get_scrip_code.assert_called_once_with("RELIANCE", "NSE")
        mock_date_to_timestamp_ms.assert_any_call("2023-01-01")
        mock_date_to_timestamp_ms.assert_any_call("2023-01-01", end_of_day=True)
        mock_split_date_range.assert_called_once_with("2023-01-01", "2023-01-01", ANY)
        mock_get_api_response.assert_called_once()

        assert not df.empty
        assert len(df) == 2
        assert df.iloc['open'] == 100
        assert df.iloc['volume'] == 1200
        mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.indmoney.api.data.BrokerData._get_scrip_code')
    @patch('app.utils.logging.logger')
    async def test_get_history_unsupported_interval(self, mock_logger, mock_get_scrip_code, mock_settings):
        mock_settings.INDMONEY_MARKETDATA_URL = "http://testurl.com"
        broker_data = BrokerData("test_auth_token")
        with pytest.raises(Exception, match="Unsupported interval 'unsupported'"):
            await broker_data.get_history("RELIANCE", "NSE", "unsupported", "2023-01-01", "2023-01-01")
        mock_get_scrip_code.assert_not_called()
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.indmoney.api.data.get_api_response')
    @patch('app.web.broker.broker.indmoney.api.data.BrokerData._get_scrip_code')
    @patch('app.web.broker.broker.indmoney.api.data.BrokerData._date_to_timestamp_ms')
    @patch('app.web.broker.broker.indmoney.api.data.BrokerData._split_date_range')
    @patch('app.utils.logging.logger')
    async def test_get_history_api_error(self, mock_logger, mock_split_date_range, mock_date_to_timestamp_ms, mock_get_scrip_code, mock_get_api_response, mock_settings):
        mock_settings.INDMONEY_MARKETDATA_URL = "http://testurl.com"
        mock_get_scrip_code.return_value = "NSE_12345"
        mock_date_to_timestamp_ms.side_effect = [1672531200000, 1672617599000, 1672531200000, 1672617599000]
        mock_split_date_range.return_value = [("2023-01-01", "2023-01-01")]
        mock_get_api_response.side_effect = Exception("API error during history fetch")

        broker_data = BrokerData("test_auth_token")
        with pytest.raises(Exception, match="Error fetching historical data"):
            await broker_data.get_history("RELIANCE", "NSE", "1h", "2023-01-01", "2023-01-01")

        mock_get_scrip_code.assert_called_once()
        mock_get_api_response.assert_called_once()
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.web.broker.broker.indmoney.api.data.get_api_response')
    @patch('app.web.broker.broker.indmoney.api.data.BrokerData._get_scrip_code', return_value=None)
    @patch('app.web.broker.broker.indmoney.api.data.BrokerData._date_to_timestamp_ms')
    @patch('app.web.broker.broker.indmoney.api.data.BrokerData._split_date_range')
    @patch('app.utils.logging.logger')
    async def test_get_history_get_scrip_code_error(self, mock_logger, mock_split_date_range, mock_date_to_timestamp_ms, mock_get_scrip_code, mock_get_api_response, mock_settings):
        mock_settings.INDMONEY_MARKETDATA_URL = "http://testurl.com"
        broker_data = BrokerData("test_auth_token")
        with pytest.raises(Exception, match="Could not find security ID"):
            await broker_data.get_history("RELIANCE", "NSE", "1h", "2023-01-01", "2023-01-01")

        mock_get_scrip_code.assert_called_once()
        mock_get_api_response.assert_not_called()
        mock_logger.error.assert_called_once()

    @patch('app.utils.logging.logger')
    def test_date_to_timestamp_ms(self, mock_logger):
        broker_data = BrokerData("test_auth_token")
        # Test with datetime object
        dt_object = datetime(2023, 1, 1, 0, 0, 0, tzinfo=IST)
        timestamp = broker_data._date_to_timestamp_ms(dt_object)
        assert timestamp == 1672531200000  # Corresponds to 2023-01-01 00:00:00 IST

        dt_object_eod = datetime(2023, 1, 1, 23, 59, 59, tzinfo=IST)
        timestamp_eod = broker_data._date_to_timestamp_ms(dt_object_eod, end_of_day=True)
        assert timestamp_eod == 1672617599000 # Corresponds to 2023-01-01 23:59:59 IST

        # Test with string input
        timestamp_str = broker_data._date_to_timestamp_ms("2023-01-01")
        assert timestamp_str == 1672531200000
        mock_logger.error.assert_not_called()

    @patch('app.utils.logging.logger')
    def test_date_to_timestamp_ms_none_input(self, mock_logger):
        broker_data = BrokerData("test_auth_token")
        with pytest.raises(ValueError):
            broker_data._date_to_timestamp_ms(None)
        mock_logger.error.assert_not_called()

    @pytest.mark.parametrize("start_date, end_date, max_days, expected_ranges", [
        ("2023-01-01", "2023-01-01", 7, [("2023-01-01", "2023-01-01")]),
        ("2023-01-01", "2023-01-07", 7, [("2023-01-01", "2023-01-07")]),
        ("2023-01-01", "2023-01-08", 7, [("2023-01-01", "2023-01-07"), ("2023-01-08", "2023-01-08")]),
        ("2023-01-01", "2023-01-15", 7, [("2023-01-01", "2023-01-07"), ("2023-01-08", "2023-01-14"), ("2023-01-15", "2023-01-15")]),
        ("2023-01-01", "2023-02-01", 14, [("2023-01-01", "2023-01-14"), ("2023-01-15", "2023-01-28"), ("2023-01-29", "2023-02-01")])
    ])
    @patch('app.utils.logging.logger')
    def test_split_date_range(self, mock_logger, start_date, end_date, max_days, expected_ranges):
        broker_data = BrokerData("test_auth_token")
        result = broker_data._split_date_range(start_date, end_date, max_days)
        assert result == expected_ranges
        mock_logger.error.assert_not_called()

class TestIndmoneyFunds:
    @pytest.fixture(autouse=True)
    def setup(self, mock_httpx_client, mock_get_url, mock_logger):
        self.mock_httpx_client = mock_httpx_client
        self.mock_get_url = mock_get_url
        self.mock_logger = mock_logger
        self.auth_token = "test_auth_token"

    def _create_mock_response(self, status_code, json_data=None, text_data=None):
        mock_response = MagicMock()
        mock_response.status_code = status_code
        if json_data is not None:
            mock_response.json.return_value = json_data
            mock_response.text = json.dumps(json_data)
        elif text_data is not None:
            mock_response.text = text_data
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", text_data, 0)
        else:
            mock_response.text = ""
        return mock_response

    @pytest.mark.asyncio
    async def test_get_margin_data_success(self):
        expected_data = {
            "status": "success",
            "data": {
                "sod_balance": 10000.0,
                "withdrawal_balance": 5000.0,
                "pledge_received": 2000.0,
                "realized_pnl": 100.0,
                "unrealized_pnl": 50.0,
                "funds_added": 1000.0,
                "funds_withdrawn": 200.0,
                "detailed_avl_balance": {
                    "option_sell": 3000.0,
                    "future": 4000.0,
                    "option_buy": 1000.0,
                    "eq_mis": 500.0,
                    "eq_cnc": 600.0,
                    "eq_mtf": 700.0
                }
            }
        }
        self.mock_httpx_client.get.return_value = self._create_mock_response(200, json_data=expected_data)

        result = get_margin_data(self.auth_token)

        assert result == {
            "availablecash": "5000.00",
            "collateral": "2000.00",
            "m2munrealized": "50.00",
            "m2mrealized": "100.00",
            "utiliseddebits": "5000.00",
            "sod_balance": "10000.00",
            "funds_added": "1000.00",
            "funds_withdrawn": "200.00",
            "option_sell_balance": "3000.00",
            "future_balance": "4000.00",
            "option_buy_balance": "1000.00",
            "eq_mis_balance": "500.00",
            "eq_cnc_balance": "600.00",
            "eq_mtf_balance": "700.00"
        }
        self.mock_httpx_client.get.assert_called_once()
        self.mock_logger.info.assert_called()
        self.mock_logger.debug.assert_called_with(f"Raw response from Indmoney API: {expected_data}")
        self.mock_logger.info.assert_called_with("Successfully processed margin data from Indmoney API")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [400, 401, 404, 500])
    async def test_get_margin_data_http_errors(self, status_code):
        self.mock_httpx_client.get.return_value = self._create_mock_response(status_code, text_data="Error Message")

        result = get_margin_data(self.auth_token)

        assert result == DEFAULT_MARGIN_RESPONSE
        self.mock_httpx_client.get.assert_called_once()
        self.mock_logger.error.assert_called_with(f"Error fetching margin data: HTTP {status_code} - Error Message...")

    @pytest.mark.asyncio
    async def test_get_margin_data_cloudflare_error(self):
        cloudflare_html = "<html><body>Just a moment... Cloudflare</body></html>"
        self.mock_httpx_client.get.return_value = self._create_mock_response(403, text_data=cloudflare_html)

        result = get_margin_data(self.auth_token)

        assert "_error" in result
        assert "Cloudflare protection - requires browser access" in result["_error"]
        self.mock_httpx_client.get.assert_called_once()
        self.mock_logger.error.assert_called_with(f"Error fetching margin data: HTTP 403 - {cloudflare_html[:200]}...")
        self.mock_logger.warning.assert_any_call("Cloudflare protection detected - API requires browser-based access")

    @pytest.mark.asyncio
    async def test_get_margin_data_api_specific_error(self):
        api_error_response = {"status": "error", "message": "API specific error"}
        self.mock_httpx_client.get.return_value = self._create_mock_response(200, json_data=api_error_response)

        result = get_margin_data(self.auth_token)

        assert result == DEFAULT_MARGIN_RESPONSE
        self.mock_httpx_client.get.assert_called_once()
        self.mock_logger.error.assert_called_with("API returned error: API specific error")

    @pytest.mark.asyncio
    async def test_get_margin_data_json_decode_error(self):
        invalid_json_text = "This is not JSON"
        self.mock_httpx_client.get.return_value = self._create_mock_response(200, text_data=invalid_json_text)

        result = get_margin_data(self.auth_token)

        assert result == DEFAULT_MARGIN_RESPONSE
        self.mock_httpx_client.get.assert_called_once()
        self.mock_logger.error.assert_called_with("Failed to parse API response: Invalid JSON")
        self.mock_logger.debug.assert_called_with(f"Response content: {invalid_json_text[:500]}...")

    @pytest.mark.asyncio
    async def test_get_margin_data_empty_data_response(self):
        empty_data_response = {"status": "success", "data": {}}
        self.mock_httpx_client.get.return_value = self._create_mock_response(200, json_data=empty_data_response)

        result = get_margin_data(self.auth_token)

        assert result == DEFAULT_MARGIN_RESPONSE
        self.mock_httpx_client.get.assert_called_once()
        self.mock_logger.error.assert_called_with("No data in API response")

    @pytest.mark.asyncio
    async def test_get_margin_data_general_exception(self):
        self.mock_httpx_client.get.side_effect = Exception("Network connection failed")

        result = get_margin_data(self.auth_token)

        assert result == DEFAULT_MARGIN_RESPONSE
        self.mock_httpx_client.get.assert_called_once()
        self.mock_logger.error.assert_called_with("Unexpected error in get_margin_data: Network connection failed", exc_info=True)



class TestIndmoneyOrderAPI:
    @pytest.fixture(autouse=True)
    def setup(self, mock_httpx_client, mock_get_url, mock_logger):
        self.mock_httpx_client = mock_httpx_client
        self.mock_get_url = mock_get_url
        self.mock_logger = mock_logger
        self.auth_token = "test_auth_token"
        self.endpoint = "/test-endpoint"
        self.url = f"https://api.indmoney.com{self.endpoint}"

    def _create_mock_response(self, status_code, json_data=None, text_data=None):
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.status = status_code  # For compatibility
        if json_data is not None:
            mock_response.text = json.dumps(json_data)
        elif text_data is not None:
            mock_response.text = text_data
        else:
            mock_response.text = ""
        return mock_response

    def get_headers(self):
        return {
            'Authorization': self.auth_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    def test_get_api_response_success(self):
        expected_data = {"status": "success", "data": [{"item": "value"}]}
        self.mock_httpx_client.get.return_value = self._create_mock_response(200, json_data=expected_data)

        result = get_order_api_response(self.endpoint, self.auth_token, method="GET")

        self.mock_httpx_client.get.assert_called_once_with(self.url, headers=self.get_headers())
        assert result == expected_data['data']
        self.mock_logger.info.assert_any_call(f"Successfully fetched data from {self.endpoint}")

    @pytest.mark.parametrize("status_code", [400, 401, 404, 500])
    def test_get_api_response_http_errors(self, status_code):
        error_message = "Something went wrong"
        self.mock_httpx_client.get.return_value = self._create_mock_response(status_code, text_data=error_message)

        result = get_order_api_response(self.endpoint, self.auth_token, method="GET")

        self.mock_httpx_client.get.assert_called_once_with(self.url, headers=self.get_headers())
        assert result == {'status': 'error', 'message': f'HTTP {status_code}: {error_message}'}
        self.mock_logger.error.assert_called_once_with(f"HTTP Error {status_code} for {self.url}: {error_message}")

    def test_get_api_response_empty_response(self):
        self.mock_httpx_client.get.return_value = self._create_mock_response(200, text_data="")

        result = get_order_api_response(self.endpoint, self.auth_token, method="GET")

        self.mock_httpx_client.get.assert_called_once_with(self.url, headers=self.get_headers())
        assert result == {'status': 'error', 'message': 'Empty response from API'}
        self.mock_logger.error.assert_called_once_with(f"Empty response from {self.url}")

    def test_get_api_response_json_decode_error(self):
        invalid_json_text = "This is not JSON"
        self.mock_httpx_client.get.return_value = self._create_mock_response(200, text_data=invalid_json_text)

        result = get_order_api_response(self.endpoint, self.auth_token, method="GET")

        self.mock_httpx_client.get.assert_called_once_with(self.url, headers=self.get_headers())
        assert "Invalid JSON response" in result['message']
        self.mock_logger.error.assert_any_call(f"Failed to parse JSON response from {self.url}: Expecting value: line 1 column 1 (char 0)")
        self.mock_logger.error.assert_any_call(f"Raw response: {invalid_json_text[:500]}...")

    @pytest.mark.parametrize("api_response, expected_message", [
        ({"status": "error", "message": "API error"}, "API error"),
        ({"status": "failure", "error": {"msg": "Failure message"}}, "Failure message"),
    ])
    def test_get_api_response_api_specific_errors(self, api_response, expected_message):
        self.mock_httpx_client.get.return_value = self._create_mock_response(200, json_data=api_response)

        result = get_order_api_response(self.endpoint, self.auth_token, method="GET")

        self.mock_httpx_client.get.assert_called_once_with(self.url, headers=self.get_headers())
        assert result == api_response
        self.mock_logger.error.assert_called_once_with(f"API Error: {expected_message}")

    @patch('app.web.broker.broker.indmoney.api.order_api.get_api_response')
    def test_get_positions_success(self, mock_get_api_response):
        """Test successful retrieval of positions."""
        expected_positions = [{"symbol": "RELIANCE", "net_qty": 10}]
        mock_get_api_response.return_value = expected_positions

        result = get_positions(self.auth_token)

        mock_get_api_response.assert_called_once_with("/portfolio/positions", self.auth_token)
        assert result == expected_positions
        self.mock_logger.warning.assert_not_called()

    @patch('app.web.broker.broker.indmoney.api.order_api.get_api_response')
    def test_get_positions_api_returns_none(self, mock_get_api_response):
        """Test that get_positions returns an empty list when the API returns None."""
        mock_get_api_response.return_value = None

        result = get_positions(self.auth_token)

        mock_get_api_response.assert_called_once_with("/portfolio/positions", self.auth_token)
        assert result == []
        self.mock_logger.warning.assert_called_once_with("get_api_response returned None for positions, returning empty list")

    @patch('app.web.broker.broker.indmoney.api.order_api.get_api_response')
    @patch('app.web.broker.broker.indmoney.api.order_api.logger')
    def test_get_positions_exception(self, mock_logger, mock_get_api_response):
        """Test that get_positions handles exceptions and returns an empty list."""
        test_exception = Exception("API fetch failed")
        mock_get_api_response.side_effect = test_exception

        result = get_positions(self.auth_token)

        mock_get_api_response.assert_called_once_with("/portfolio/positions", self.auth_token)
        assert result == []
        mock_logger.error.assert_called_once_with(f"Exception in get_positions: {test_exception}")

    @patch('app.web.broker.broker.indmoney.api.order_api.get_api_response')
    @patch('app.web.broker.broker.indmoney.api.order_api.logger')
    def test_get_positions_api_error_response(self, mock_logger, mock_get_api_response):
        """Test that get_positions handles an API error response dictionary."""
        error_response = {'status': 'error', 'message': 'Failed to fetch positions'}
        mock_get_api_response.return_value = error_response

        result = get_positions(self.auth_token)

        mock_get_api_response.assert_called_once_with("/portfolio/positions", self.auth_token)
        assert result == error_response
        mock_logger.error.assert_not_called() # The error is already logged by get_api_response, get_positions just returns it.
        mock_logger.warning.assert_not_called()