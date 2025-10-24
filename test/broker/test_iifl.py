def test_iifl_placeholder():
    # TODO: Implement actual tests for IIFL broker integration.
    assert True
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.web.broker.broker.iifl.api.auth_api import authenticate_broker, get_feed_token
from app.web.broker.broker.iifl.api.data import BrokerData, get_api_response
from app.web.broker.broker.iifl.api.order_api import (
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
from app.web.broker.broker.iifl.api.funds import get_margin_data

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
    def mock_get_feed_token(self):
        with patch('app.web.broker.broker.iifl.api.auth_api.get_feed_token') as mock_get_feed_token:
            yield mock_get_feed_token

    @pytest.mark.asyncio
    async def test_authenticate_broker_success(self, mock_settings, mock_httpx_client, mock_logger, mock_get_feed_token):
        mock_httpx_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"type": "success", "result": {"token": "test_auth_token"}}
        )
        mock_get_feed_token.return_value = ("test_feed_token", "test_user_id", None)

        request_token = "dummy_request_token"
        auth_token, feed_token, user_id, error = authenticate_broker(request_token)

        mock_httpx_client.post.assert_called_once()
        assert auth_token == "test_auth_token"
        assert feed_token == "test_feed_token"
        assert user_id == "test_user_id"
        assert error is None
        mock_logger.info.assert_any_call("Auth Token: test_auth_token")
        mock_logger.info.assert_any_call("Feed Token: test_feed_token")

    @pytest.mark.asyncio
    async def test_authenticate_broker_api_error(self, mock_settings, mock_httpx_client, mock_logger, mock_get_feed_token):
        mock_httpx_client.post.return_value = MagicMock(
            status_code=400,
            json=lambda: {"message": "Invalid credentials"}
        )
        mock_get_feed_token.return_value = ("test_feed_token", "test_user_id", None)

        request_token = "dummy_request_token"
        auth_token, feed_token, user_id, error = authenticate_broker(request_token)

        mock_httpx_client.post.assert_called_once()
        assert auth_token is None
        assert feed_token is None
        assert user_id is None
        assert "API error: Invalid credentials" in error
        mock_logger.info.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_broker_exception(self, mock_settings, mock_httpx_client, mock_logger, mock_get_feed_token):
        mock_httpx_client.post.side_effect = Exception("Network error")
        mock_get_feed_token.return_value = ("test_feed_token", "test_user_id", None)

        request_token = "dummy_request_token"
        auth_token, feed_token, user_id, error = authenticate_broker(request_token)

        mock_httpx_client.post.assert_called_once()
        assert auth_token is None
        assert feed_token is None
        assert user_id is None
        assert "Error during authentication: Network error" in error
        mock_logger.info.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_broker_feed_token_error(self, mock_settings, mock_httpx_client, mock_logger, mock_get_feed_token):
        mock_httpx_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"type": "success", "result": {"token": "test_auth_token"}}
        )
        mock_get_feed_token.return_value = (None, None, "Feed token request failed")

        request_token = "dummy_request_token"
        auth_token, feed_token, user_id, error = authenticate_broker(request_token)

        mock_httpx_client.post.assert_called_once()
        assert auth_token == "test_auth_token"
        assert feed_token is None
        assert user_id is None
        assert "Feed token error: Feed token request failed" in error
        mock_logger.info.assert_any_call("Auth Token: test_auth_token")
        mock_logger.info.assert_not_called("Feed Token: test_feed_token")

class TestIIFLFeedToken:
    @pytest.fixture
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
        response = get_api_response(endpoint, auth, method)

        mock_httpx_client.get.assert_called_once()
        assert response == {"type": "success", "data": "test_data"}
        mock_logger.info.assert_called()
        mock_logger.error.assert_not_called()

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
        response = get_api_response(endpoint, auth, method, payload)

        mock_httpx_client.post.assert_called_once_with(
            f"{'https://api.iifl.com/marketdata'}{endpoint}",
            headers={'authorization': 'test_auth_token', 'Content-Type': 'application/json'},
            json=payload
        )
        assert response == {"type": "success", "data": "test_data"}
        mock_logger.info.assert_called()
        mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_api_response_api_error(self, mock_httpx_client, mock_logger):
        mock_httpx_client.get.return_value = MagicMock(
            status_code=400,
            json=lambda: {"type": "error", "message": "API error"},
            text='{"type": "error", "message": "API error"}',
            headers={}
        )

        endpoint = "/test"
        auth = "test_auth_token"
        method = "GET"
        response = get_api_response(endpoint, auth, method)

        mock_httpx_client.get.assert_called_once()
        assert response == {"type": "error", "message": "API error"}
        mock_logger.info.assert_called()
        mock_logger.error.assert_not_called() # The function does not log as error for 4xx responses.

    @pytest.mark.asyncio
    async def test_get_api_response_exception(self, mock_httpx_client, mock_logger):
        mock_httpx_client.get.side_effect = Exception("Network issue")

        endpoint = "/test"
        auth = "test_auth_token"
        method = "GET"
        
        with pytest.raises(Exception, match="Network issue"):
            get_api_response(endpoint, auth, method)

        mock_httpx_client.get.assert_called_once()
        mock_logger.error.assert_called_once_with("API request failed: Network issue")
class TestIIFLBrokerData:
    @pytest.fixture
    def mock_db_session(self):
        with patch('app.web.broker.broker.iifl.api.data.db_session') as mock_db_session:
            mock_session = MagicMock()
            mock_db_session.return_value.__enter__.return_value = mock_session
            yield mock_session

    @pytest.fixture
    def mock_symtoken(self):
        with patch('app.web.broker.broker.iifl.api.data.SymToken') as mock_symtoken:
            yield mock_symtoken

    @pytest.fixture
    def mock_get_br_symbol(self):
        with patch('app.web.broker.broker.iifl.api.data.get_br_symbol') as mock_get_br_symbol:
            yield mock_get_br_symbol

    @pytest.mark.asyncio
    async def test_get_instrument_token_success(self, mock_db_session, mock_symtoken, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "BR_SYMBOL"
        mock_symbol_info = MagicMock()
        mock_symbol_info.token = "12345"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_symbol_info

        broker_data = BrokerData("test_auth_token")
        token_info, brexchange = broker_data._get_instrument_token("TEST", "NSE")

        mock_get_br_symbol.assert_called_once_with("TEST", "NSE")
        mock_db_session.query.assert_called_once_with(mock_symtoken)
        mock_symtoken.exchange == "NSE"
        mock_symtoken.brsymbol == "BR_SYMBOL"
        assert token_info == mock_symbol_info
        assert brexchange == 1

    @pytest.mark.asyncio
    async def test_get_instrument_token_unknown_exchange(self, mock_db_session, mock_symtoken, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "BR_SYMBOL"

        broker_data = BrokerData("test_auth_token")
        with pytest.raises(Exception, match="Unknown exchange segment: UNKNOWN"):
            broker_data._get_instrument_token("TEST", "UNKNOWN")

    @pytest.mark.asyncio
    async def test_get_instrument_token_not_found(self, mock_db_session, mock_symtoken, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "BR_SYMBOL"
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        broker_data = BrokerData("test_auth_token")
        with pytest.raises(Exception, match="Could not find exchange token for NSE:BR_SYMBOL"):
            broker_data._get_instrument_token("TEST", "NSE")
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
            json=lambda: {"type": "success", "result": {"token": "test_feed_token", "userID": "test_user_id"}}
        )

        feed_token, user_id, error = get_feed_token()

        mock_httpx_client.post.assert_called_once()
        assert feed_token == "test_feed_token"
        assert user_id == "test_user_id"
        assert error is None
        mock_logger.info.assert_any_call("Feed Token: test_feed_token")

    @pytest.mark.asyncio
    async def test_get_feed_token_api_error(self, mock_settings, mock_httpx_client, mock_logger):
        mock_httpx_client.post.return_value = MagicMock(
            status_code=400,
            json=lambda: {"description": "Invalid market credentials"}
        )

        feed_token, user_id, error = get_feed_token()

        mock_httpx_client.post.assert_called_once()
        assert feed_token is None
        assert user_id is None
        assert "API Error (Feed): Invalid market credentials" in error
        mock_logger.info.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_feed_token_exception(self, mock_settings, mock_httpx_client, mock_logger):
        mock_httpx_client.post.side_effect = Exception("Network error for feed token")

        feed_token, user_id, error = get_feed_token()

        mock_httpx_client.post.assert_called_once()
        assert feed_token is None
        assert user_id is None
        assert "An exception occurred: Network error for feed token" in error
        mock_logger.info.assert_not_called()

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.web.broker.broker.iifl.api.auth_api import authenticate_broker, get_feed_token
from app.web.broker.broker.iifl.api.data import BrokerData, get_api_response
from app.web.broker.broker.iifl.api.data import SymToken, db_session, get_br_symbol


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
        with patch('app.web.broker.broker.iifl.api.auth_api.get_feed_token') as mock_get_feed_token:
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
        auth_token, feed_token, user_id, error = authenticate_broker(request_token)

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
        auth_token, feed_token, user_id, error = authenticate_broker(request_token)

        assert auth_token is None
        assert feed_token is None
        assert user_id is None
        assert "API Error" in error
        mock_logger.error.assert_called_with("Failed to authenticate broker: API Error")

    @pytest.mark.asyncio
    async def test_authenticate_broker_exception(self, mock_settings, mock_httpx_client, mock_logger, mock_get_feed_token_func):
        mock_httpx_client.post.side_effect = Exception("Network Error")

        request_token = "dummy_request_token"
        auth_token, feed_token, user_id, error = authenticate_broker(request_token)

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
        auth_token, feed_token, user_id, error = authenticate_broker(request_token)

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

        feed_token, user_id, error = get_feed_token()

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

        feed_token, user_id, error = get_feed_token()

        assert feed_token is None
        assert user_id is None
        assert "API Error" in error
        mock_logger.error.assert_called_with("Failed to get feed token: API Error")

    @pytest.mark.asyncio
    async def test_get_feed_token_exception(self, mock_settings, mock_httpx_client, mock_logger):
        mock_httpx_client.post.side_effect = Exception("Network Error")

        feed_token, user_id, error = get_feed_token()

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
        response = get_api_response(endpoint, auth, method, payload)

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
        response = get_api_response(endpoint, auth, method, params=params)

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
            get_api_response(endpoint, auth, method, payload)

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
            get_api_response(endpoint, auth, method, payload)

        assert "API request failed: Network Error" in str(excinfo.value)
        mock_logger.error.assert_called_with(f"API request failed: Network Error")


class TestIIFLBrokerData_GetInstrumentToken:
    @pytest.fixture
    def mock_db_session(self):
        with patch('app.web.broker.broker.iifl.api.data.db_session') as mock_db_session:
            mock_session = MagicMock()
            mock_db_session.return_value.__enter__.return_value = mock_session
            yield mock_session

    @pytest.fixture
    def mock_symtoken(self):
        with patch('app.web.broker.broker.iifl.api.data.SymToken') as mock_symtoken:
            yield mock_symtoken

    @pytest.fixture
    def mock_get_br_symbol(self):
        with patch('app.web.broker.broker.iifl.api.data.get_br_symbol') as mock_get_br_symbol:
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
        with patch('app.web.broker.broker.iifl.api.data.get_api_response') as mock_get_api_response:
            yield mock_get_api_response

    @pytest.fixture
    def mock_logger(self):
        with patch('app.utils.logging.logger', new_callable=MagicMock) as mock_logger:
            yield mock_logger

    def test_fetch_market_data_success(self, mock_get_api_response, mock_logger):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"listQuotes": ['{"Touchline": {"LastTradedPrice": 100}}']}
        }
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        token = {"exchangeSegment": 1, "exchangeInstrumentID": "12345"}
        message_code = 1502

        result = broker_data._fetch_market_data(token, message_code)

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

    def test_fetch_market_data_api_error_no_response(self, mock_get_api_response, mock_logger):
        mock_get_api_response.return_value = None
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        token = {"exchangeSegment": 1, "exchangeInstrumentID": "12345"}
        message_code = 1502

        result = broker_data._fetch_market_data(token, message_code)

        assert result is None
        mock_logger.warning.assert_called_with("Error fetching market data (code 1502): No response")
        mock_logger.error.assert_not_called()

    def test_fetch_market_data_api_error_type_error(self, mock_get_api_response, mock_logger):
        mock_get_api_response.return_value = {"type": "error", "description": "API Error"}
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        token = {"exchangeSegment": 1, "exchangeInstrumentID": "12345"}
        message_code = 1502

        result = broker_data._fetch_market_data(token, message_code)

        assert result is None
        mock_logger.warning.assert_called_with("Error fetching market data (code 1502): API Error")
        mock_logger.error.assert_not_called()

    def test_fetch_market_data_empty_list_quotes(self, mock_get_api_response, mock_logger):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"listQuotes": []}
        }
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        token = {"exchangeSegment": 1, "exchangeInstrumentID": "12345"}
        message_code = 1502

        result = broker_data._fetch_market_data(token, message_code)

        assert result is None
        mock_logger.warning.assert_called_with("Empty listQuotes in response (code 1502)")
        mock_logger.error.assert_not_called()

    def test_fetch_market_data_empty_raw_data(self, mock_get_api_response, mock_logger):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"listQuotes": [None]}
        }
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        token = {"exchangeSegment": 1, "exchangeInstrumentID": "12345"}
        message_code = 1502

        result = broker_data._fetch_market_data(token, message_code)

        assert result is None
        mock_logger.warning.assert_called_with("No data in response (code 1502)")
        mock_logger.error.assert_not_called()

    def test_fetch_market_data_exception(self, mock_get_api_response, mock_logger):
        mock_get_api_response.side_effect = Exception("Network Error")
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        token = {"exchangeSegment": 1, "exchangeInstrumentID": "12345"}
        message_code = 1502

        result = broker_data._fetch_market_data(token, message_code)

        assert result is None
        mock_logger.error.assert_called_with("Error in _fetch_market_data (code 1502): Network Error", exc_info=True)


class TestIIFLBrokerData_GetQuotes:
    @pytest.fixture
    def mock_get_instrument_token(self):
        with patch('app.web.broker.broker.iifl.api.data.BrokerData._get_instrument_token') as mock_method:
            yield mock_method

    @pytest.fixture
    def mock_fetch_market_data(self):
        with patch('app.web.broker.broker.iifl.api.data.BrokerData._fetch_market_data') as mock_method:
            yield mock_method

    @pytest.fixture
    def mock_logger(self):
        with patch('app.utils.logging.logger', new_callable=MagicMock) as mock_logger:
            yield mock_logger

    def test_get_quotes_success_no_oi(self, mock_get_instrument_token, mock_fetch_market_data, mock_logger):
        mock_get_instrument_token.return_value = (MagicMock(token="12345"), 1)
        mock_fetch_market_data.side_effect = [
            {"Touchline": {"AskInfo": {"Price": 101}, "BidInfo": {"Price": 99}, "High": 105, "Low": 95, "LastTradedPrice": 100, "Open": 98, "Close": 97, "TotalTradedQuantity": 1000}},
            None # No OI data
        ]
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        
        result = broker_data.get_quotes("TEST", "NSE")

        mock_get_instrument_token.assert_called_once_with("TEST", "NSE")
        assert mock_fetch_market_data.call_count == 2
        mock_fetch_market_data.assert_any_call({'exchangeSegment': 1, 'exchangeInstrumentID': '12345'}, 1502)
        mock_fetch_market_data.assert_any_call({'exchangeSegment': 1, 'exchangeInstrumentID': '12345'}, 1510)

        assert result == {
            'ask': 101, 'bid': 99, 'high': 105, 'low': 95, 'ltp': 100,
            'open': 98, 'prev_close': 97, 'volume': 1000, 'oi': 0
        }
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_called_with("Failed to fetch OI data: 'NoneType' object is not subscriptable")


    def test_get_quotes_success_with_oi(self, mock_get_instrument_token, mock_fetch_market_data, mock_logger):
        mock_get_instrument_token.return_value = (MagicMock(token="12345"), 1)
        mock_fetch_market_data.side_effect = [
            {"Touchline": {"AskInfo": {"Price": 101}, "BidInfo": {"Price": 99}, "High": 105, "Low": 95, "LastTradedPrice": 100, "Open": 98, "Close": 97, "TotalTradedQuantity": 1000}},
            {"OpenInterest": 5000}
        ]
        broker_data = BrokerData("test_auth_token", "test_feed_token")

        result = broker_data.get_quotes("TEST", "NSE")

        mock_get_instrument_token.assert_called_once_with("TEST", "NSE")
        assert mock_fetch_market_data.call_count == 2
        mock_fetch_market_data.assert_any_call({'exchangeSegment': 1, 'exchangeInstrumentID': '12345'}, 1502)
        mock_fetch_market_data.assert_any_call({'exchangeSegment': 1, 'exchangeInstrumentID': '12345'}, 1510)

        assert result == {
            'ask': 101, 'bid': 99, 'high': 105, 'low': 95, 'ltp': 100,
            'open': 98, 'prev_close': 97, 'volume': 1000, 'oi': 5000
        }
        mock_logger.error.assert_not_called()
        mock_logger.debug.assert_called_with("Added OI data: 5000")

    def test_get_quotes_fetch_market_data_failure(self, mock_get_instrument_token, mock_fetch_market_data, mock_logger):
        mock_get_instrument_token.return_value = (MagicMock(token="12345"), 1)
        mock_fetch_market_data.return_value = None  # Simulate failure to fetch market data

        broker_data = BrokerData("test_auth_token", "test_feed_token")

        with pytest.raises(Exception, match="Failed to fetch market data"):
            broker_data.get_quotes("TEST", "NSE")
        
        mock_get_instrument_token.assert_called_once_with("TEST", "NSE")
        mock_fetch_market_data.assert_called_once_with({'exchangeSegment': 1, 'exchangeInstrumentID': '12345'}, 1502)
        mock_logger.error.assert_called_once_with("Error fetching quotes: Failed to fetch market data")

    def test_get_quotes_exception(self, mock_get_instrument_token, mock_fetch_market_data, mock_logger):
        mock_get_instrument_token.side_effect = Exception("Instrument token error")
        broker_data = BrokerData("test_auth_token", "test_feed_token")

        with pytest.raises(Exception, match="Error fetching quotes: Instrument token error"):
            broker_data.get_quotes("TEST", "NSE")
        
        mock_get_instrument_token.assert_called_once_with("TEST", "NSE")
        mock_fetch_market_data.assert_not_called()
        mock_logger.error.assert_called_once_with("Error fetching quotes: Instrument token error")


class TestIIFLBrokerData_GetHistory:
    @pytest.fixture
    def mock_get_instrument_token(self):
        with patch('app.web.broker.broker.iifl.api.data.BrokerData._get_instrument_token') as mock_method:
            yield mock_method

    @pytest.fixture
    def mock_get_br_symbol(self):
        with patch('app.web.broker.broker.iifl.api.data.get_br_symbol') as mock_method:
            yield mock_method

    @pytest.fixture
    def mock_get_api_response(self):
        with patch('app.web.broker.broker.iifl.api.data.get_api_response') as mock_method:
            yield mock_method

    @pytest.fixture
    def mock_logger(self):
        with patch('app.utils.logging.logger', new_callable=MagicMock) as mock_logger:
            yield mock_logger

    @pytest.mark.asyncio
    async def test_get_history_success_1m(self, mock_get_instrument_token, mock_get_br_symbol, mock_get_api_response, mock_logger):
        mock_get_br_symbol.return_value = "TESTBR"
        mock_get_instrument_token.return_value = (MagicMock(token="12345"), 1)
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"dataReponse": "1678886400|100.0|101.0|99.0|100.5|1000,1678886460|100.5|102.0|100.0|101.5|1200"}
        }

        broker_data = BrokerData("test_auth_token", "test_feed_token")
        
        # Patch datetime to control current time in the loop
        with patch('app.web.broker.broker.iifl.api.data.datetime') as mock_datetime:
            from datetime import datetime as real_datetime
            mock_datetime.now.return_value = real_datetime(2023, 3, 15, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: real_datetime(*args, **kw) # Ensure real datetime behavior for other calls

            df = await broker_data.get_history("TEST", "NSE", "1m", "2023-03-15", "2023-03-15")

            mock_get_br_symbol.assert_called_once_with("TEST", "NSE")
            mock_get_instrument_token.assert_called_once_with("TEST", "NSE")
            mock_get_api_response.assert_called_once()
            mock_logger.error.assert_not_called()
            assert not df.empty
            assert len(df) == 2
            assert df.iloc[0]['open'] == 100.0
            assert df.iloc[1]['close'] == 101.5

    @pytest.mark.asyncio
    async def test_get_history_success_1d(self, mock_get_instrument_token, mock_get_br_symbol, mock_get_api_response, mock_logger):
        mock_get_br_symbol.return_value = "TESTBR"
        mock_get_instrument_token.return_value = (MagicMock(token="12345"), 1)
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"dataReponse": "1678838400|100.0|105.0|98.0|102.0|50000"}
        }

        broker_data = BrokerData("test_auth_token", "test_feed_token")
        
        with patch('app.web.broker.broker.iifl.api.data.datetime') as mock_datetime:
            from datetime import datetime as real_datetime
            mock_datetime.now.return_value = real_datetime(2023, 3, 15, 10, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: real_datetime(*args, **kw)

            df = await broker_data.get_history("TEST", "NSE", "1d", "2023-03-14", "2023-03-14")

            mock_get_br_symbol.assert_called_once_with("TEST", "NSE")
            mock_get_instrument_token.assert_called_once_with("TEST", "NSE")
            mock_get_api_response.assert_called_once()
            mock_logger.error.assert_not_called()
            assert not df.empty
            assert len(df) == 1
            assert df.iloc[0]['open'] == 100.0
            assert df.iloc[0]['close'] == 102.0

    @pytest.mark.asyncio
    async def test_get_history_invalid_interval(self, mock_logger):
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        
        df = await broker_data.get_history("TEST", "NSE", "5s", "2023-03-15", "2023-03-15")

        assert df.empty
        mock_logger.error.assert_called_once_with("Unsupported timeframe: 5s")

class TestIIFLBrokerData_GetMarketDepth:
    @pytest.fixture
    def mock_get_instrument_token(self):
        with patch('app.web.broker.broker.iifl.api.data.BrokerData._get_instrument_token') as mock_method:
            yield mock_method

    @pytest.fixture
    def mock_fetch_market_data(self):
        with patch('app.web.broker.broker.iifl.api.data.BrokerData._fetch_market_data') as mock_method:
            yield mock_method

    @pytest.fixture
    def mock_logger(self):
        with patch('app.utils.logging.logger', new_callable=MagicMock) as mock_logger:
            yield mock_logger

    def test_get_market_depth_success(self, mock_get_instrument_token, mock_fetch_market_data, mock_logger):
        mock_get_instrument_token.return_value = (MagicMock(token="12345"), 1)
        mock_fetch_market_data.return_value = {
            "Touchline": {
                "AskInfo": [{"Price": 101, "Quantity": 50}, {"Price": 102, "Quantity": 100}],
                "BidInfo": [{"Price": 99, "Quantity": 70}, {"Price": 98, "Quantity": 120}]
            }
        }
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        
        result = broker_data.get_market_depth("TEST", "NSE")

        mock_get_instrument_token.assert_called_once_with("TEST", "NSE")
        mock_fetch_market_data.assert_called_once_with({'exchangeSegment': 1, 'exchangeInstrumentID': '12345'}, 1502)
        mock_logger.error.assert_not_called()
        
        assert result == {
            'buy': [
                {'price': 99, 'quantity': 70},
                {'price': 98, 'quantity': 120}
            ],
            'sell': [
                {'price': 101, 'quantity': 50},
                {'price': 102, 'quantity': 100}
            ]
        }

    def test_get_market_depth_fetch_market_data_failure(self, mock_get_instrument_token, mock_fetch_market_data, mock_logger):
        mock_get_instrument_token.return_value = (MagicMock(token="12345"), 1)
        mock_fetch_market_data.return_value = None  # Simulate failure to fetch market data
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        
        result = broker_data.get_market_depth("TEST", "NSE")

        mock_get_instrument_token.assert_called_once_with("TEST", "NSE")
        mock_fetch_market_data.assert_called_once_with({'exchangeSegment': 1, 'exchangeInstrumentID': '12345'}, 1502)
        mock_logger.error.assert_called_once_with("Error fetching market depth: Failed to fetch market data")
        assert result == {'buy': [], 'sell': []}

    def test_get_market_depth_exception(self, mock_get_instrument_token, mock_fetch_market_data, mock_logger):
        mock_get_instrument_token.side_effect = Exception("Instrument token error")
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        
        result = broker_data.get_market_depth("TEST", "NSE")

        mock_get_instrument_token.assert_called_once_with("TEST", "NSE")
        mock_fetch_market_data.assert_not_called()
        mock_logger.error.assert_called_once_with("Error fetching market depth: Instrument token error")
        assert result == {'buy': [], 'sell': []}

class TestIIFLBrokerData_GetDepth:
    @pytest.fixture
    def mock_get_instrument_token(self):
        with patch('app.web.broker.broker.iifl.api.data.BrokerData._get_instrument_token') as mock_method:
            yield mock_method

    @pytest.fixture
    def mock_fetch_market_data(self):
        with patch('app.web.broker.broker.iifl.api.data.BrokerData._fetch_market_data') as mock_method:
            yield mock_method

    @pytest.fixture
    def mock_logger(self):
        with patch('app.utils.logging.logger', new_callable=MagicMock) as mock_logger:
            yield mock_logger

    def test_get_depth_success(self, mock_get_instrument_token, mock_fetch_market_data, mock_logger):
        mock_get_instrument_token.return_value = (MagicMock(token="12345"), 1)
        mock_fetch_market_data.return_value = {
            "Touchline": {
                "AskInfo": [{"Price": 101, "Quantity": 50}, {"Price": 102, "Quantity": 100}],
                "BidInfo": [{"Price": 99, "Quantity": 70}, {"Price": 98, "Quantity": 120}]
            }
        }
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        
        result = broker_data.get_depth("TEST", "NSE")

        mock_get_instrument_token.assert_called_once_with("TEST", "NSE")
        mock_fetch_market_data.assert_called_once_with({'exchangeSegment': 1, 'exchangeInstrumentID': '12345'}, 1502)
        mock_logger.error.assert_not_called()
        
        assert result == {
            'buy': [
                {'price': 99, 'quantity': 70},
                {'price': 98, 'quantity': 120}
            ],
            'sell': [
                {'price': 101, 'quantity': 50},
                {'price': 102, 'quantity': 100}
            ]
        }

    def test_get_depth_fetch_market_data_failure(self, mock_get_instrument_token, mock_fetch_market_data, mock_logger):
        mock_get_instrument_token.return_value = (MagicMock(token="12345"), 1)
        mock_fetch_market_data.return_value = None  # Simulate failure to fetch market data
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        
        result = broker_data.get_depth("TEST", "NSE")

        mock_get_instrument_token.assert_called_once_with("TEST", "NSE")
        mock_fetch_market_data.assert_called_once_with({'exchangeSegment': 1, 'exchangeInstrumentID': '12345'}, 1502)
        mock_logger.error.assert_called_once_with("Error fetching market depth: Failed to fetch market data")
        assert result == {'buy': [], 'sell': []}

    def test_get_depth_exception(self, mock_get_instrument_token, mock_fetch_market_data, mock_logger):
        mock_get_instrument_token.side_effect = Exception("Instrument token error")
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        
        result = broker_data.get_depth("TEST", "NSE")

        mock_get_instrument_token.assert_called_once_with("TEST", "NSE")
        mock_fetch_market_data.assert_not_called()
        mock_logger.error.assert_called_once_with("Error fetching market depth: Instrument token error")
        assert result == {'buy': [], 'sell': []}


class TestIIFLBrokerData_GetIntervals:
    def test_get_intervals_success(self):
        broker_data = BrokerData("test_auth_token", "test_feed_token")
        intervals = broker_data.get_intervals()
        expected_intervals = ["1s", "1m", "2m", "3m", "5m", "10m", "15m", "30m", "60m", "D"]
        assert intervals == expected_intervals


class TestIIFLOrderApi:
    @pytest.fixture
    def mock_httpx_client(self):
        with patch('app.utils.httpx_client.get_httpx_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get = AsyncMock()
            mock_client.post = AsyncMock()
            mock_client.request = AsyncMock()
            mock_client.delete = AsyncMock() # Add mock for delete method
            mock_client.put = AsyncMock() # Add mock for put method
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
        response = get_api_response(endpoint, auth, method)

        mock_httpx_client.get.assert_called_once_with(
            f"{'https://api.iifl.com/interactive'}{endpoint}",
            headers={'authorization': 'test_auth_token', 'Content-Type': 'application/json'}
        )
        assert response == {"type": "success", "data": "test_data"}
        mock_logger.info.assert_called()
        mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_order_book_success(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "success", "data": [{"orderid": "123"}]}

            auth_token = "test_auth_token"
            result = get_order_book(auth_token)

            mock_get_api_response.assert_called_once_with("/orders", auth_token)
            assert result == {"type": "success", "data": [{"orderid": "123"}]}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_order_book_api_error(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "error", "message": "API error"}

            auth_token = "test_auth_token"
            result = get_order_book(auth_token)

            mock_get_api_response.assert_called_once_with("/orders", auth_token)
            assert result == {"type": "error", "message": "API error"}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_order_book_exception(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.side_effect = Exception("Network issue")

            auth_token = "test_auth_token"
            with pytest.raises(Exception, match="Network issue"):
                get_order_book(auth_token)

            mock_get_api_response.assert_called_once_with("/orders", auth_token)
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_trade_book_success(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "success", "data": [{"tradeid": "456"}]}

            auth_token = "test_auth_token"
            result = get_trade_book(auth_token)

            mock_get_api_response.assert_called_once_with("/tradebook", auth_token)
            assert result == {"type": "success", "data": [{"tradeid": "456"}]}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_trade_book_api_error(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "error", "message": "API error"}

            auth_token = "test_auth_token"
            result = get_trade_book(auth_token)

            mock_get_api_response.assert_called_once_with("/tradebook", auth_token)
            assert result == {"type": "error", "message": "API error"}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_trade_book_exception(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.side_effect = Exception("Network issue")

            auth_token = "test_auth_token"
            with pytest.raises(Exception, match="Network issue"):
                get_trade_book(auth_token)

            mock_get_api_response.assert_called_once_with("/tradebook", auth_token)
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_positions_success(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "success", "data": [{"symbol": "TEST", "qty": 10}]}

            auth_token = "test_auth_token"
            result = get_positions(auth_token)

            mock_get_api_response.assert_called_once_with("/position", auth_token)
            assert result == {"type": "success", "data": [{"symbol": "TEST", "qty": 10}]}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_positions_api_error(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "error", "message": "API error"}

            auth_token = "test_auth_token"
            result = get_positions(auth_token)

            mock_get_api_response.assert_called_once_with("/position", auth_token)
            assert result == {"type": "error", "message": "API error"}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_positions_exception(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.side_effect = Exception("Network issue")

            auth_token = "test_auth_token"
            with pytest.raises(Exception, match="Network issue"):
                get_positions(auth_token)

            mock_get_api_response.assert_called_once_with("/position", auth_token)
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_holdings_success(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "success", "data": [{"symbol": "TEST", "qty": 5}]}

            auth_token = "test_auth_token"
            result = get_holdings(auth_token)

            mock_get_api_response.assert_called_once_with("/holdings", auth_token)
            assert result == {"type": "success", "data": [{"symbol": "TEST", "qty": 5}]}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_holdings_api_error(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "error", "message": "API error"}

            auth_token = "test_auth_token"
            result = get_holdings(auth_token)

            mock_get_api_response.assert_called_once_with("/holdings", auth_token)
            assert result == {"type": "error", "message": "API error"}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_holdings_exception(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.side_effect = Exception("Network issue")

            auth_token = "test_auth_token"
            with pytest.raises(Exception, match="Network issue"):
                get_holdings(auth_token)

            mock_get_api_response.assert_called_once_with("/holdings", auth_token)
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_open_position_success(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "success", "data": [{"symbol": "TEST", "qty": 20}]}

            auth_token = "test_auth_token"
            result = get_open_position(auth_token)

            mock_get_api_response.assert_called_once_with("/openposition", auth_token)
            assert result == {"type": "success", "data": [{"symbol": "TEST", "qty": 20}]}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_open_position_api_error(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "error", "message": "API error"}

            auth_token = "test_auth_token"
            result = get_open_position(auth_token)

            mock_get_api_response.assert_called_once_with("/openposition", auth_token)
            assert result == {"type": "error", "message": "API error"}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_open_position_exception(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.side_effect = Exception("Network issue")

            auth_token = "test_auth_token"
            with pytest.raises(Exception, match="Network issue"):
                get_open_position(auth_token)

            mock_get_api_response.assert_called_once_with("/openposition", auth_token)
            mock_logger.error.assert_not_called()

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
        response = get_api_response(endpoint, auth, method, payload)

        mock_httpx_client.post.assert_called_once_with(
            f"{'https://api.iifl.com/interactive'}{endpoint}",
            headers={'authorization': 'test_auth_token', 'Content-Type': 'application/json'},
            json=payload
        )
        assert response == {"type": "success", "data": "test_data"}
        mock_logger.info.assert_called()
        mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_api_response_api_error(self, mock_httpx_client, mock_logger):
        mock_httpx_client.get.return_value = MagicMock(
            status_code=400,
            json=lambda: {"type": "error", "message": "API error"},
            text='{"type": "error", "message": "API error"}',
            headers={}
        )

        endpoint = "/test"
        auth = "test_auth_token"
        method = "GET"
        response = get_api_response(endpoint, auth, method)

        mock_httpx_client.get.assert_called_once()
        assert response == {"type": "error", "message": "API error"}
        mock_logger.info.assert_called()
        mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_api_response_exception(self, mock_httpx_client, mock_logger):
        mock_httpx_client.get.side_effect = Exception("Network issue")

        endpoint = "/test"
        auth = "test_auth_token"
        method = "GET"
        
        with pytest.raises(Exception, match="Network issue"):
            get_api_response(endpoint, auth, method)

        mock_httpx_client.get.assert_called_once()
        # The logger.error is not called in the get_api_response in order_api.py
        mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_place_order_api_success(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "success", "data": {"orderid": "ORDER123"}}
            
            auth_token = "test_auth_token"
            order_data = {"symbol": "TEST", "qty": 10}
            result = place_order_api(order_data, auth_token)

            mock_get_api_response.assert_called_once_with("/placeorder", auth_token, method="POST", payload=order_data)
            assert result == {"type": "success", "data": {"orderid": "ORDER123"}}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_place_smartorder_api_success(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "success", "data": {"orderid": "SMARTORDER123"}}
            
            auth_token = "test_auth_token"
            order_data = {"symbol": "TEST", "qty": 10, "price": 100}
            result = place_smartorder_api(order_data, auth_token)

            mock_get_api_response.assert_called_once_with("/placesmartorder", auth_token, method="POST", payload=order_data)
            assert result == {"type": "success", "data": {"orderid": "SMARTORDER123"}}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_place_smartorder_api_api_error(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "error", "message": "Smart order API error"}

            auth_token = "test_auth_token"
            order_data = {"symbol": "TEST", "qty": 10, "price": 100}
            result = place_smartorder_api(order_data, auth_token)

            mock_get_api_response.assert_called_once_with("/placesmartorder", auth_token, method="POST", payload=order_data)
            assert result == {"type": "error", "message": "Smart order API error"}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_place_smartorder_api_exception(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.side_effect = Exception("Smart order network issue")

            auth_token = "test_auth_token"
            order_data = {"symbol": "TEST", "qty": 10, "price": 100}
            with pytest.raises(Exception, match="Smart order network issue"):
                place_smartorder_api(order_data, auth_token)

            mock_get_api_response.assert_called_once_with("/placesmartorder", auth_token, method="POST", payload=order_data)
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_all_positions_success(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "success", "data": {"message": "All positions closed"}}
            
            auth_token = "test_auth_token"
            result = close_all_positions(auth_token)

            mock_get_api_response.assert_called_once_with("/closeallpositions", auth_token, method="POST")
            assert result == {"type": "success", "data": {"message": "All positions closed"}}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_all_positions_api_error(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "error", "message": "Close all positions API error"}

            auth_token = "test_auth_token"
            result = close_all_positions(auth_token)

            mock_get_api_response.assert_called_once_with("/closeallpositions", auth_token, method="POST")
            assert result == {"type": "error", "message": "Close all positions API error"}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_all_positions_exception(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.side_effect = Exception("Close all positions network issue")

            auth_token = "test_auth_token"
            with pytest.raises(Exception, match="Close all positions network issue"):
                close_all_positions(auth_token)

            mock_get_api_response.assert_called_once_with("/closeallpositions", auth_token, method="POST")
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "success", "data": {"message": "Order cancelled"}}
            
            auth_token = "test_auth_token"
            order_id = "ORDER123"
            result = cancel_order(order_id, auth_token)

            mock_get_api_response.assert_called_once_with(f"/cancelorder/{order_id}", auth_token, method="DELETE")
            assert result == {"type": "success", "data": {"message": "Order cancelled"}}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_order_api_error(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "error", "message": "Cancel order API error"}

            auth_token = "test_auth_token"
            order_id = "ORDER123"
            result = cancel_order(order_id, auth_token)

            mock_get_api_response.assert_called_once_with(f"/cancelorder/{order_id}", auth_token, method="DELETE")
            assert result == {"type": "error", "message": "Cancel order API error"}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_modify_order_success(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "success", "data": {"message": "Order modified"}}

            auth_token = "test_auth_token"
            order_id = "ORDER123"
            new_order_data = {"qty": 20}
            result = modify_order(order_id, new_order_data, auth_token)

            mock_get_api_response.assert_called_once_with(f"/modifyorder/{order_id}", auth_token, method="PUT", payload=new_order_data)
            assert result == {"type": "success", "data": {"message": "Order modified"}}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_modify_order_api_error(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "error", "message": "Modify order API error"}

            auth_token = "test_auth_token"
            order_id = "ORDER123"
            new_order_data = {"qty": 20}
            result = modify_order(order_id, new_order_data, auth_token)

            mock_get_api_response.assert_called_once_with(f"/modifyorder/{order_id}", auth_token, method="PUT", payload=new_order_data)
            assert result == {"type": "error", "message": "Modify order API error"}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_modify_order_exception(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.side_effect = Exception("Modify order network issue")

            auth_token = "test_auth_token"
            order_id = "ORDER123"
            new_order_data = {"qty": 20}
            with pytest.raises(Exception, match="Modify order network issue"):
                modify_order(order_id, new_order_data, auth_token)

            mock_get_api_response.assert_called_once_with(f"/modifyorder/{order_id}", auth_token, method="PUT", payload=new_order_data)
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_all_orders_api_success(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "success", "data": {"message": "All orders cancelled"}}

            auth_token = "test_auth_token"
            result = cancel_all_orders_api(auth_token)

            mock_get_api_response.assert_called_once_with("/cancelallorder", auth_token, method="DELETE")
            assert result == {"type": "success", "data": {"message": "All orders cancelled"}}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_all_orders_api_api_error(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "error", "message": "Cancel all orders API error"}

            auth_token = "test_auth_token"
            result = cancel_all_orders_api(auth_token)

            mock_get_api_response.assert_called_once_with("/cancelallorder", auth_token, method="DELETE")
            assert result == {"type": "error", "message": "Cancel all orders API error"}
            mock_logger.error.assert_not_called()

class TestIIFLFundsApi:
    @pytest.fixture
    def mock_get_httpx_client(self):
        with patch('app.web.broker.broker.iifl.api.funds.get_httpx_client') as mock_client:
            yield mock_client

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
        result = get_margin_data(auth_token)

        expected_result = {
            "availablecash": "10000.00",
            "collateral": "5000.00",
            "m2munrealized": "1000.00",
            "m2mrealized": "500.00",
            "utiliseddebits": "2000.00",
        }
        assert result == expected_result
        mock_get_httpx_client.return_value.get.assert_called_once_with(f"{INTERACTIVE_URL}/user/balance", headers={'authorization': auth_token, 'Content-Type': 'application/json'})
        mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_margin_data_empty_response(self, mock_get_httpx_client, mock_logger):
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": {"BalanceList": []}}
        mock_get_httpx_client.return_value.get.return_value = mock_response

        auth_token = "test_auth_token"
        result = get_margin_data(auth_token)

        assert result == {}
        mock_get_httpx_client.return_value.get.assert_called_once_with(f"{INTERACTIVE_URL}/user/balance", headers={'authorization': auth_token, 'Content-Type': 'application/json'})
        mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_margin_data_api_error(self, mock_get_httpx_client, mock_logger):
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "API error"}
        mock_get_httpx_client.return_value.get.return_value = mock_response

        auth_token = "test_auth_token"
        result = get_margin_data(auth_token)

        assert result == {}
        mock_get_httpx_client.return_value.get.assert_called_once_with(f"{INTERACTIVE_URL}/user/balance", headers={'authorization': auth_token, 'Content-Type': 'application/json'})
        mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_margin_data_exception(self, mock_get_httpx_client, mock_logger):
        mock_get_httpx_client.return_value.get.side_effect = Exception("Network issue")

        auth_token = "test_auth_token"
        with pytest.raises(Exception, match="Network issue"):
            get_margin_data(auth_token)

        mock_get_httpx_client.return_value.get.assert_called_once_with(f"{INTERACTIVE_URL}/user/balance", headers={'authorization': auth_token, 'Content-Type': 'application/json'})
        mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_all_orders_api_exception(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.side_effect = Exception("Cancel all orders network issue")

            auth_token = "test_auth_token"
            with pytest.raises(Exception, match="Cancel all orders network issue"):
                cancel_all_orders_api(auth_token)

            mock_get_api_response.assert_called_once_with("/cancelallorder", auth_token, method="DELETE")
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_order_exception(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.side_effect = Exception("Cancel order network issue")

            auth_token = "test_auth_token"
            order_id = "ORDER123"
            with pytest.raises(Exception, match="Cancel order network issue"):
                cancel_order(order_id, auth_token)

            mock_get_api_response.assert_called_once_with(f"/cancelorder/{order_id}", auth_token, method="DELETE")
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_place_order_api_api_error(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.return_value = {"type": "error", "message": "API error"}

            auth_token = "test_auth_token"
            order_data = {"symbol": "TEST", "qty": 10}
            result = place_order_api(order_data, auth_token)

            mock_get_api_response.assert_called_once_with("/placeorder", auth_token, method="POST", payload=order_data)
            assert result == {"type": "error", "message": "API error"}
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_place_order_api_exception(self, mock_httpx_client, mock_logger):
        with patch('app.web.broker.broker.iifl.api.order_api.get_api_response') as mock_get_api_response:
            mock_get_api_response.side_effect = Exception("Network issue")

            auth_token = "test_auth_token"
            order_data = {"symbol": "TEST", "qty": 10}
            with pytest.raises(Exception, match="Network issue"):
                place_order_api(order_data, auth_token)

            mock_get_api_response.assert_called_once_with("/placeorder", auth_token, method="POST", payload=order_data)
            mock_logger.error.assert_not_called()