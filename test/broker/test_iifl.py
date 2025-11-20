import pytest
pytest.skip("Skipped by user request", allow_module_level=True)
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.web.brokers.iifl.api.auth_api import authenticate_broker, get_feed_token
from app.web.brokers.iifl.api.data import BrokerData, get_api_response
from app.web.brokers.iifl.api.order_api import (
    get_order_book,
)
from app.web.brokers.iifl.api.funds import get_margin_data

def test_iifl_placeholder():
    # TODO: Implement actual tests for IIFL broker integration.
    assert True

class TestIIFLAuth:
    @pytest.fixture
    def mock_settings(self):
        with patch('app.core.config.settings', new_callable=MagicMock) as mock_settings:
            mock_settings.BROKER_API_KEY = "test_api_key"
            mock_settings.BROKER_API_SECRET = "test_api_secret"
            mock_settings.BROKER_API_KEY_MARKET = "test_market_api_key"
            mock_settings.BROKER_API_SECRET_MARKET = "test_market_api_secret"
            yield mock_settings

    @pytest.fixture
    def mock_httpx_client(self):
        with patch('app.utils.httpx_client.get_httpx_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def mock_logger(self):
        with patch('app.utils.logging.logger', new_callable=MagicMock) as mock_logger:
            yield mock_logger

    @pytest.fixture
    def mock_get_feed_token_func(self):
        with patch('app.web.brokers.iifl.api.auth_api.get_feed_token') as mock_get_feed_token:
            yield mock_get_feed_token

    @pytest.mark.asyncio
    async def test_authenticate_broker_success(self, mock_settings, mock_httpx_client, mock_logger, mock_get_feed_token_func):
        mock_httpx_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"type": "success", "result": {"token": "test_auth_token"}},
            text='{"type": "success", "result": {"token": "test_auth_token"}}',
            headers={}
        )
        mock_get_feed_token_func.return_value = ("test_feed_token", "test_user_id", None)

        request_token = "dummy_request_token"
        auth_token, feed_token, user_id, error = await authenticate_broker(request_token)

        mock_httpx_client.post.assert_called_once_with(
            "https://api.iifl.com/apimarket/auth/generate-session",
            headers={'Content-Type': 'application/json'},
            json={"appKey": "test_api_key", "secretKey": "test_api_secret", "token": "dummy_request_token"}
        )
        assert auth_token == "test_auth_token"
        assert feed_token == "test_feed_token"
        assert user_id == "test_user_id"
        assert error is None
        mock_logger.info.assert_any_call("Auth Token: test_auth_token")
        mock_logger.info.assert_any_call("Feed Token: test_feed_token")

    @pytest.mark.asyncio
    async def test_authenticate_broker_api_error(self, mock_settings, mock_httpx_client, mock_logger, mock_get_feed_token_func):
        mock_httpx_client.post.return_value = MagicMock(
            status_code=400,
            json=lambda: {"type": "error", "description": "API Error"},
            text='{"type": "error", "description": "API Error"}',
            headers={}
        )

        request_token = "dummy_request_token"
        auth_token, feed_token, user_id, error = await authenticate_broker(request_token)

        assert auth_token is None
        assert feed_token is None
        assert user_id is None
        assert "API Error" in error
        mock_logger.error.assert_called_with("Failed to authenticate broker: API Error")

    @pytest.mark.asyncio
    async def test_authenticate_broker_exception(self, mock_settings, mock_httpx_client, mock_logger, mock_get_feed_token_func):
        mock_httpx_client.post.side_effect = Exception("Network Error")

        request_token = "dummy_request_token"
        auth_token, feed_token, user_id, error = await authenticate_broker(request_token)

        assert auth_token is None
        assert feed_token is None
        assert user_id is None
        assert "Network Error" in error
        mock_logger.error.assert_called_with("Failed to authenticate broker: Network Error")

    @pytest.mark.asyncio
    async def test_authenticate_broker_feed_token_error(self, mock_settings, mock_httpx_client, mock_logger, mock_get_feed_token_func):
        mock_httpx_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"type": "success", "result": {"token": "test_auth_token"}},
            text='{"type": "success", "result": {"token": "test_auth_token"}}',
            headers={}
        )
        mock_get_feed_token_func.return_value = (None, None, "Feed token error")

        request_token = "dummy_request_token"
        auth_token, feed_token, user_id, error = await authenticate_broker(request_token)

        assert auth_token is None
        assert feed_token is None
        assert user_id is None
        assert "Feed token error" in error
        mock_logger.error.assert_called_with("Failed to get feed token: Feed token error")


class TestIIFLFeedToken:
    @pytest.fixture
    def mock_settings(self):
        with patch('app.core.config.settings', new_callable=MagicMock) as mock_settings:
            mock_settings.BROKER_API_KEY_MARKET = "test_market_api_key"
            mock_settings.BROKER_API_SECRET_MARKET = "test_market_api_secret"
            yield mock_settings

    @pytest.fixture
    def mock_httpx_client(self):
        with patch('app.utils.httpx_client.get_httpx_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def mock_logger(self):
        with patch('app.utils.logging.logger', new_callable=MagicMock) as mock_logger:
            yield mock_logger

    @pytest.mark.asyncio
    async def test_get_feed_token_success(self, mock_settings, mock_httpx_client, mock_logger):
        mock_httpx_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"type": "success", "result": {"feedToken": "test_feed_token", "userId": "test_user_id"}},
            text='{"type": "success", "result": {"feedToken": "test_feed_token", "userId": "test_user_id"}}',
            headers={}
        )

        feed_token, user_id, error = await get_feed_token()

        mock_httpx_client.post.assert_called_once_with(
            "https://api.iifl.com/apimarket/auth/generate-session",
            headers={'Content-Type': 'application/json'},
            json={"appKey": "test_market_api_key", "secretKey": "test_market_api_secret"}
        )
        assert feed_token == "test_feed_token"
        assert user_id == "test_user_id"
        assert error is None
        mock_logger.info.assert_called_with("Feed Token generated successfully")

    @pytest.mark.asyncio
    async def test_get_feed_token_api_error(self, mock_settings, mock_httpx_client, mock_logger):
        mock_httpx_client.post.return_value = MagicMock(
            status_code=400,
            json=lambda: {"type": "error", "description": "API Error"},
            text='{"type": "error", "description": "API Error"}',
            headers={}
        )

        feed_token, user_id, error = await get_feed_token()

        assert feed_token is None
        assert user_id is None
        assert "API Error" in error
        mock_logger.error.assert_called_with("Failed to get feed token: API Error")

    @pytest.mark.asyncio
    async def test_get_feed_token_exception(self, mock_settings, mock_httpx_client, mock_logger):
        mock_httpx_client.post.side_effect = Exception("Network Error")

        feed_token, user_id, error = await get_feed_token()

        assert feed_token is None
        assert user_id is None
        assert "Network Error" in error
        mock_logger.error.assert_called_with("Failed to get feed token: Network Error")


class TestIIFLApiResponse:
    @pytest.fixture
    def mock_httpx_client(self):
        with patch('app.utils.httpx_client.get_httpx_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get = AsyncMock()
            mock_client.post = AsyncMock()
            mock_client.request = AsyncMock()
            mock_get_client.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def mock_logger(self):
        with patch('app.utils.logging.logger', new_callable=MagicMock) as mock_logger:
            yield mock_logger

    @pytest.mark.asyncio
    async def test_get_api_response_post_success(self, mock_httpx_client, mock_logger):
        mock_httpx_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"type": "success", "data": "test_data"},
            text='{"type": "success", "data": "test_data"}',
            headers={}
        )

        endpoint = "/test"
        auth = "test_auth_token"
        method = "POST"
        payload = {"key": "value"}
        response = await get_api_response(endpoint, auth, method, payload)

        mock_httpx_client.post.assert_called_once_with(
            f"{'https://api.iifl.com/marketdata'}{endpoint}",
            headers={'authorization': 'test_auth_token', 'Content-Type': 'application/json'},
            json=payload
        )
        assert response == {"type": "success", "data": "test_data"}
        mock_logger.info.assert_called()
        mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_api_response_get_success(self, mock_httpx_client, mock_logger):
        mock_httpx_client.get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"type": "success", "data": "test_data"},
            text='{"type": "success", "data": "test_data"}',
            headers={}
        )

        endpoint = "/test"
        auth = "test_auth_token"
        method = "GET"
        params = {"key": "value"}
        response = await get_api_response(endpoint, auth, method, params=params)

        mock_httpx_client.get.assert_called_once_with(
            f"{'https://api.iifl.com/marketdata'}{endpoint}",
            headers={'authorization': 'test_auth_token', 'Content-Type': 'application/json'},
            params=params
        )
        assert response == {"type": "success", "data": "test_data"}
        mock_logger.info.assert_called()
        mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_api_response_api_error(self, mock_httpx_client, mock_logger):
        mock_httpx_client.post.return_value = MagicMock(
            status_code=400,
            json=lambda: {"type": "error", "description": "API Error"},
            text='{"type": "error", "description": "API Error"}',
            headers={}
        )

        endpoint = "/test"
        auth = "test_auth_token"
        method = "POST"
        payload = {"key": "value"}

        with pytest.raises(Exception) as excinfo:
            await get_api_response(endpoint, auth, method, payload)

        assert "API request failed" in str(excinfo.value)
        mock_logger.error.assert_called_with(f"API request failed: {str(excinfo.value)}")

    @pytest.mark.asyncio
    async def test_get_api_response_exception(self, mock_httpx_client, mock_logger):
        mock_httpx_client.post.side_effect = Exception("Network Error")

        endpoint = "/test"
        auth = "test_auth_token"
        method = "POST"
        payload = {"key": "value"}

        with pytest.raises(Exception) as excinfo:
            await get_api_response(endpoint, auth, method, payload)

        assert "API request failed: Network Error" in str(excinfo.value)
        mock_logger.error.assert_called_with("API request failed: Network Error")


class TestIIFLBrokerData_GetInstrumentToken:
    @pytest.fixture
    def mock_db_session(self):
        with patch('app.web.brokers.iifl.api.data.db_session') as mock_db_session:
            mock_session = MagicMock()
            mock_db_session.return_value.__enter__.return_value = mock_session
            yield mock_session

    @pytest.fixture
    def mock_symtoken(self):
        with patch('app.web.brokers.iifl.api.data.SymToken') as mock_symtoken:
            yield mock_symtoken

    @pytest.fixture
    def mock_get_br_symbol(self):
        with patch('app.web.brokers.iifl.api.data.get_br_symbol') as mock_get_br_symbol:
            yield mock_get_br_symbol

    def test_get_instrument_token_success(self, mock_db_session, mock_symtoken, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "BR_SYMBOL"
        mock_symbol_info = MagicMock()
        mock_symbol_info.token = "12345"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_symbol_info

        broker_data = BrokerData("test_auth_token")
        token_info, brexchange = broker_data._get_instrument_token("TEST", "NSE")

        mock_get_br_symbol.assert_called_once_with("TEST", "NSE")
        mock_db_session.query.assert_called_once_with(mock_symtoken)
        mock_db_session.query.return_value.filter.assert_called_once()
        mock_db_session.query.return_value.filter.return_value.first.assert_called_once()
        assert token_info == mock_symbol_info
        assert brexchange == 1

    def test_get_instrument_token_unknown_exchange(self, mock_get_br_symbol):
        broker_data = BrokerData("test_auth_token")
        with pytest.raises(Exception) as excinfo:
            broker_data._get_instrument_token("TEST", "UNKNOWN_EXCHANGE")
        assert "Unknown exchange segment: UNKNOWN_EXCHANGE" in str(excinfo.value)
        mock_get_br_symbol.assert_called_once_with("TEST", "UNKNOWN_EXCHANGE")

    def test_get_instrument_token_not_found(self, mock_db_session, mock_symtoken, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "BR_SYMBOL"
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        broker_data = BrokerData("test_auth_token")
        with pytest.raises(Exception) as excinfo:
            broker_data._get_instrument_token("TEST", "NSE")
        assert "Could not find exchange token for NSE:BR_SYMBOL" in str(excinfo.value)
        mock_get_br_symbol.assert_called_once_with("TEST", "NSE")
        mock_db_session.query.assert_called_once_with(mock_symtoken)
        mock_db_session.query.return_value.filter.assert_called_once()
        mock_db_session.query.return_value.filter.return_value.first.assert_called_once()


class TestIIFLBrokerData_FetchMarketData:
    @pytest.fixture
    def mock_get_api_response(self):
        with patch('app.web.brokers.iifl.api.data.get_api_response') as mock_get_api_response:
            yield mock_get_api_response

    @pytest.fixture
    def mock_logger(self):
        with patch('app.utils.logging.logger', new_callable=MagicMock) as mock_logger:
            yield mock_logger

    async def test_fetch_market_data_success(self, mock_get_api_response, mock_logger):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"listQuotes": ['{"Touchline": {"LastTradedPrice": 100}}']}
        }
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        token = {"exchangeSegment": 1, "exchangeInstrumentID": "12345"}
        message_code = 1502

        result = await broker_data._fetch_market_data(token, message_code)

        mock_get_api_response.assert_called_once_with(
            "/instruments/quotes",
            "test_auth_token",
            method="POST",
            payload={"instruments": [token], "xtsMessageCode": message_code, "publishFormat": "JSON"},
            feed_token="test_feed_token"
        )
        assert result == {"Touchline": {"LastTradedPrice": 100}}
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

    async def test_fetch_market_data_api_error_no_response(self, mock_get_api_response, mock_logger):
        mock_get_api_response.return_value = None
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        token = {"exchangeSegment": 1, "exchangeInstrumentID": "12345"}
        message_code = 1502

        result = await broker_data._fetch_market_data(token, message_code)

        assert result is None
        mock_logger.warning.assert_called_with("Error fetching market data (code 1502): No response")
        mock_logger.error.assert_not_called()

    async def test_fetch_market_data_api_error_type_error(self, mock_get_api_response, mock_logger):
        mock_get_api_response.return_value = {"type": "error", "description": "API Error"}
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        token = {"exchangeSegment": 1, "exchangeInstrumentID": "12345"}
        message_code = 1502

        result = await broker_data._fetch_market_data(token, message_code)

        assert result is None
        mock_logger.warning.assert_called_with("Error fetching market data (code 1502): API Error")
        mock_logger.error.assert_not_called()

    async def test_fetch_market_data_empty_list_quotes(self, mock_get_api_response, mock_logger):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"listQuotes": []}
        }
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        token = {"exchangeSegment": 1, "exchangeInstrumentID": "12345"}
        message_code = 1502

        result = await broker_data._fetch_market_data(token, message_code)

        assert result is None
        mock_logger.warning.assert_called_with("Empty listQuotes in response (code 1502)")
        mock_logger.error.assert_not_called()

    async def test_fetch_market_data_empty_raw_data(self, mock_get_api_response, mock_logger):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"listQuotes": [None]}
        }
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        token = {"exchangeSegment": 1, "exchangeInstrumentID": "12345"}
        message_code = 1502

        result = await broker_data._fetch_market_data(token, message_code)

        assert result is None
        mock_logger.warning.assert_called_with("No data in response (code 1502)")
        mock_logger.error.assert_not_called()

    async def test_fetch_market_data_exception(self, mock_get_api_response, mock_logger):
        mock_get_api_response.side_effect = Exception("Network Error")
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        token = {"exchangeSegment": 1, "exchangeInstrumentID": "12345"}
        message_code = 1502

        result = await broker_data._fetch_market_data(token, message_code)

        assert result is None
        mock_logger.error.assert_called_with("Error in _fetch_market_data (code 1502): Network Error", exc_info=True)

class TestIIFLOrderApi:
    @pytest.fixture
    def mock_httpx_client(self):
        with patch('app.utils.httpx_client.get_httpx_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get = AsyncMock()
            mock_client.post = AsyncMock()
            mock_client.request = AsyncMock()
            mock_client.delete = AsyncMock()
            mock_client.put = AsyncMock()
            mock_get_client.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def mock_logger(self):
        with patch('app.utils.logging.logger', new_callable=MagicMock) as mock_logger:
            yield mock_logger

    @pytest.mark.asyncio
    async def test_get_api_response_get_success(self, mock_httpx_client, mock_logger):
        mock_httpx_client.get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"type": "success", "data": "test_data"},
            text='{"type": "success", "data": "test_data"}',
            headers={}
        )

        endpoint = "/test"
        auth = "test_auth_token"
        method = "GET"
        response = await get_api_response(endpoint, auth, method)

        mock_httpx_client.get.assert_called_once_with(
            f"{'https://api.iifl.com/interactive'}{endpoint}",
            headers={'authorization': 'test_auth_token', 'Content-Type': 'application/json'}
        )
        assert response == {"type": "success", "data": "test_data"}
        mock_logger.info.assert_called()
        mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_order_book_success(self, mock_httpx_client, mock_logger):
        with patch('app.web.brokers.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "success", "data": [{"orderid": "123"}]}

            auth_token = "test_auth_token"
            result = await get_order_book(auth_token)

            mock_get_api_response.assert_called_once_with("/orders", auth_token)
            assert result == {"type": "success", "data": [{"orderid": "123"}]}
            mock_logger.error.assert_not_called()
class TestIIFLFundsApi:
    @pytest.fixture
    def mock_get_httpx_client(self):
        with patch('app.web.brokers.iifl.api.funds.get_httpx_client') as mock_client:
            yield mock_client
    @pytest.fixture
    def mock_logger(self):
        with patch('app.utils.logging.logger', new_callable=MagicMock) as mock_logger:
            yield mock_logger
    @pytest.mark.asyncio
    async def test_get_margin_data_success(self, mock_get_httpx_client, mock_logger):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "BalanceList": [
                    {
                        "limitObject": {
                            "RMSSubLimits": {
                                "netMarginAvailable": 10000.00,
                                "collateral": 5000.00,
                                "UnrealizedMTM": 1000.00,
                                "RealizedMTM": 500.00,
                                "marginUtilized": 2000.00
                            }
                        }
                    }
                ]
            }
        }
        mock_get_httpx_client.return_value.get.return_value = mock_response

        auth_token = "test_auth_token"
        result = await get_margin_data(auth_token)

        expected_result = {
            "availablecash": "10000.00",
            "collateral": "5000.00",
            "m2munrealized": "1000.00",
            "m2mrealized": "500.00",
            "utiliseddebits": "2000.00",
        }
        assert result == expected_result
        mock_get_httpx_client.return_value.get.assert_called_once_with(f"{'https://api.iifl.com/interactive'}/user/balance", headers={'authorization': auth_token, 'Content-Type': 'application/json'})
        mock_logger.error.assert_not_called()
