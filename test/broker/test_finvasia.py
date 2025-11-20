import pytest
pytest.skip("Skipped by user request", allow_module_level=True)
import pytest
from unittest.mock import MagicMock, patch
import json

# Import the functions and classes to be tested
from app.web.brokers.finvasia.api.auth_api import authenticate_broker, sha256_hash
from app.web.brokers.finvasia.api.data import BrokerData, get_api_response as get_data_api_response
from app.web.brokers.finvasia.api.order_api import (
    get_order_book, get_trade_book, get_positions, get_holdings,
    get_open_position, place_order_api, place_smartorder_api,
    close_all_positions, cancel_order, modify_order, cancel_all_orders_api
)

# Fixtures for mocking dependencies
@pytest.fixture
def mock_settings():
    with patch('app.core.config.settings') as mock_settings:
        mock_settings.BROKER_API_SECRET = 'test_secret'
        mock_settings.BROKER_API_KEY = 'test_api_key'
        yield mock_settings

@pytest.fixture
def mock_httpx_client():
    with patch('app.utils.httpx_client.get_httpx_client') as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_token_db():
    with patch('app.core.schemas.token_db.get_br_symbol') as mock_get_br_symbol, \
         patch('app.core.schemas.token_db.get_token') as mock_get_token, \
         patch('app.core.schemas.token_db.get_symbol') as mock_get_symbol:
        mock_get_br_symbol.return_value = 'NSE:INFY-EQ'
        mock_get_token.return_value = '12345'
        mock_get_symbol.return_value = 'INFY'
        yield {
            "get_br_symbol": mock_get_br_symbol,
            "get_token": mock_get_token,
            "get_symbol": mock_get_symbol
        }

@pytest.fixture
def mock_transform_data():
    with patch('app.web.broker.broker.finvasia.mapping.transform_data.transform_data') as mock_transform_data, \
         patch('app.web.broker.broker.finvasia.mapping.transform_data.transform_modify_order_data') as mock_transform_modify_order_data, \
         patch('app.web.broker.broker.finvasia.mapping.transform_data.map_product_type') as mock_map_product_type, \
         patch('app.web.broker.broker.finvasia.mapping.transform_data.reverse_map_product_type') as mock_reverse_map_product_type:
        mock_transform_data.side_effect = lambda data, token: {**data, "transformed": True, "token": token}
        mock_transform_modify_order_data.side_effect = lambda data, token: {**data, "transformed_modify": True, "token": token}
        mock_map_product_type.return_value = "CNC"
        mock_reverse_map_product_type.return_value = "CNC"
        yield {
            "transform_data": mock_transform_data,
            "transform_modify_order_data": mock_transform_modify_order_data,
            "map_product_type": mock_map_product_type,
            "reverse_map_product_type": mock_reverse_map_product_type
        }

# Tests for auth_api.py
def test_sha256_hash():
    assert sha256_hash("test") == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

@patch('app.web.broker.broker.finvasia.api.auth_api.get_httpx_client')
@patch('app.web.broker.broker.finvasia.api.auth_api.settings')
def test_authenticate_broker_success(mock_settings, mock_get_httpx_client):
    mock_settings.BROKER_API_SECRET = 'test_secret'
    mock_settings.BROKER_API_KEY = 'test_api_key'
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'stat': 'Ok', 'susertoken': 'mock_token_123'}
    mock_client.post.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    token, error = authenticate_broker('user1', 'pass1', '123456')
    assert token == 'mock_token_123'
    assert error is None
    mock_client.post.assert_called_once()

@patch('app.web.broker.broker.finvasia.api.auth_api.get_httpx_client')
@patch('app.web.broker.broker.finvasia.api.auth_api.settings')
def test_authenticate_broker_failure_api_error(mock_settings, mock_get_httpx_client):
    mock_settings.BROKER_API_SECRET = 'test_secret'
    mock_settings.BROKER_API_KEY = 'test_api_key'
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'stat': 'Not_Ok', 'emsg': 'Invalid credentials'}
    mock_client.post.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    token, error = authenticate_broker('user1', 'wrong_pass', '123456')
    assert token is None
    assert error == 'Invalid credentials'
    mock_client.post.assert_called_once()

@patch('app.web.broker.broker.finvasia.api.auth_api.get_httpx_client')
@patch('app.web.broker.broker.finvasia.api.auth_api.settings')
def test_authenticate_broker_failure_http_error(mock_settings, mock_get_httpx_client):
    mock_settings.BROKER_API_SECRET = 'test_secret'
    mock_settings.BROKER_API_KEY = 'test_api_key'
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = 'Bad Request'
    mock_client.post.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    token, error = authenticate_broker('user1', 'pass1', '123456')
    assert token is None
    assert error == 'Error: 400, Bad Request'
    mock_client.post.assert_called_once()

@patch('app.web.broker.broker.finvasia.api.auth_api.get_httpx_client')
@patch('app.web.broker.broker.finvasia.api.auth_api.settings')
def test_authenticate_broker_exception(mock_settings, mock_get_httpx_client):
    mock_settings.BROKER_API_SECRET = 'test_secret'
    mock_settings.BROKER_API_KEY = 'test_api_key'
    
    mock_client = MagicMock()
    mock_client.post.side_effect = Exception("Network error")
    mock_get_httpx_client.return_value = mock_client

    token, error = authenticate_broker('user1', 'pass1', '123456')
    assert token is None
    assert error == 'Network error'
    mock_client.post.assert_called_once()

# Tests for data.py
@patch('app.web.broker.broker.finvasia.api.data.get_httpx_client')
@patch('app.web.broker.broker.finvasia.api.data.settings')
@patch('app.web.broker.broker.finvasia.api.data.logger')
def test_get_data_api_response_success(mock_logger, mock_settings, mock_get_httpx_client):
    mock_settings.BROKER_API_KEY = 'test_api_key'
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({'stat': 'Ok'})
    mock_client.request.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    response = get_data_api_response("/v1/quotes", "test_auth_token")
    assert response == {'stat': 'Ok'}
    mock_client.request.assert_called_once()

@patch('app.web.broker.broker.finvasia.api.data.get_httpx_client')
@patch('app.web.broker.broker.finvasia.api.data.settings')
@patch('app.web.broker.broker.finvasia.api.data.logger')
def test_get_data_api_response_json_decode_error(mock_logger, mock_settings, mock_get_httpx_client):
    mock_settings.BROKER_API_KEY = 'test_api_key'
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "invalid json"
    mock_client.request.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    with pytest.raises(json.JSONDecodeError):
        get_data_api_response("/v1/quotes", "test_auth_token")
    mock_logger.error.assert_called_once()

@patch('app.web.broker.broker.finvasia.api.data.get_api_response')
@patch('app.web.broker.broker.finvasia.api.data.get_br_symbol')
@patch('app.web.broker.broker.finvasia.api.data.get_token')
def test_broker_data_get_quotes_success(mock_get_token, mock_get_br_symbol, mock_get_api_response):
    mock_get_api_response.return_value = {
        'stat': 'Ok', 'bid': '10.0', 'ask': '11.0', 'open': '9.0', 'high': '12.0',
        'low': '8.0', 'ltp': '10.5', 'prev_close': '9.5', 'volume': '1000', 'oi': '500'
    }
    broker_data = BrokerData("test_auth_token")
    quotes = broker_data.get_quotes("INFY", "NSE")
    assert quotes['ltp'] == 10.5
    mock_get_br_symbol.assert_called_once_with("INFY", "NSE")
    mock_get_token.assert_called_once_with("INFY", "NSE")
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.finvasia.api.data.get_api_response')
@patch('app.web.broker.broker.finvasia.api.data.get_br_symbol')
@patch('app.web.broker.broker.finvasia.api.data.get_token')
def test_broker_data_get_quotes_api_error(mock_get_token, mock_get_br_symbol, mock_get_api_response):
    mock_get_api_response.return_value = {'stat': 'Not_Ok', 'emsg': 'Invalid symbol'}
    broker_data = BrokerData("test_auth_token")
    with pytest.raises(Exception, match="Error from Finvasia API: Invalid symbol"):
        broker_data.get_quotes("INVALID", "NSE")

@patch('app.web.broker.broker.finvasia.api.data.get_api_response')
@patch('app.web.broker.broker.finvasia.api.data.get_br_symbol')
@patch('app.web.broker.broker.finvasia.api.data.get_token')
def test_broker_data_get_depth_success(mock_get_token, mock_get_br_symbol, mock_get_api_response):
    mock_get_api_response.return_value = {
        'stat': 'Ok',
        'bids': [{'quantity': 100, 'price': 10.0}],
        'asks': [{'quantity': 50, 'price': 11.0}],
        'high': '12.0', 'low': '8.0', 'ltp': '10.5', 'ltq': '10', 'open': '9.0',
        'prev_close': '9.5', 'volume': '1000', 'oi': '500'
    }
    broker_data = BrokerData("test_auth_token")
    depth = broker_data.get_depth("INFY", "NSE")
    assert depth['totalbuyqty'] == 100
    assert depth['totalsellqty'] == 50
    mock_get_br_symbol.assert_called_once_with("INFY", "NSE")
    mock_get_token.assert_called_once_with("INFY", "NSE")
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.finvasia.api.data.get_api_response')
@patch('app.web.broker.broker.finvasia.api.data.get_br_symbol')
@patch('app.web.broker.broker.finvasia.api.data.get_token')
def test_broker_data_get_history_success(mock_get_token, mock_get_br_symbol, mock_get_api_response):
    mock_get_api_response.return_value = [
        {'t': 1672531200, 'o': 100, 'h': 105, 'l': 98, 'c': 103, 'v': 1000},
        {'t': 1672617600, 'o': 103, 'h': 108, 'l': 101, 'c': 106, 'v': 1200}
    ]
    broker_data = BrokerData("test_auth_token")
    df = broker_data.get_history("INFY", "NSE", "D", "203-01-01", "2023-01-02")
    assert not df.empty
    assert df['open'].iloc == 100
    assert df['close'].iloc[-1] == 106
    mock_get_br_symbol.assert_called_once_with("INFY", "NSE")
    mock_get_token.assert_called_once_with("INFY", "NSE")
    mock_get_api_response.assert_called_once()

def test_broker_data_get_history_unsupported_interval():
    broker_data = BrokerData("test_auth_token")
    with pytest.raises(Exception, match="Unsupported interval '2h'"):
        broker_data.get_history("INFY", "NSE", "2h", "2023-01-01", "2023-01-02")

# Tests for order_api.py
@patch('app.web.broker.broker.finvasia.api.order_api.get_api_response')
def test_get_order_book_success(mock_get_api_response):
    mock_get_api_response.return_value = [{'orderid': '123', 'status': 'OPEN'}]
    orders = get_order_book("test_auth_token")
    assert orders['orderid'] == '123'
    mock_get_api_response.assert_called_once_with("/v1/orderBook", "test_auth_token", method="POST")

@patch('app.web.broker.broker.finvasia.api.order_api.get_api_response')
def test_get_trade_book_success(mock_get_api_response):
    mock_get_api_response.return_value = [{'tradeid': '456', 'symbol': 'INFY'}]
    trades = get_trade_book("test_auth_token")
    assert trades['tradeid'] == '456'
    mock_get_api_response.assert_called_once_with("/v1/tradeBook", "test_auth_token", method="POST")

@patch('app.web.broker.broker.finvasia.api.order_api.get_api_response')
def test_get_positions_success(mock_get_api_response):
    mock_get_api_response.return_value = [{'symbol': 'INFY', 'netqty': '10'}]
    positions = get_positions("test_auth_token")
    assert positions['netqty'] == '10'
    mock_get_api_response.assert_called_once_with("/v1/positionBook", "test_auth_token", method="POST")

@patch('app.web.broker.broker.finvasia.api.order_api.get_api_response')
def test_get_holdings_success(mock_get_api_response):
    mock_get_api_response.return_value = [{'symbol': 'INFY', 'holdqty': '5'}]
    holdings = get_holdings("test_auth_token")
    assert holdings['holdqty'] == '5'
    mock_get_api_response.assert_called_once_with("/v1/holdings", "test_auth_token", method="POST")

@patch('app.web.broker.broker.finvasia.api.order_api.get_positions')
@patch('app.web.broker.broker.finvasia.api.order_api.get_br_symbol')
def test_get_open_position_success(mock_get_br_symbol, mock_get_positions):
    mock_get_br_symbol.return_value = 'INFY'
    mock_get_positions.return_value = [{'tsym': 'INFY', 'exch': 'NSE', 'prd': 'CNC', 'netqty': '10'}]
    net_qty = get_open_position('INFY', 'NSE', 'CNC', 'test_auth_token')
    assert net_qty == '10'

@patch('app.web.broker.broker.finvasia.api.order_api.get_positions')
@patch('app.web.broker.broker.finvasia.api.order_api.get_br_symbol')
def test_get_open_position_no_position(mock_get_br_symbol, mock_get_positions):
    mock_get_br_symbol.return_value = 'INFY'
    mock_get_positions.return_value = []
    net_qty = get_open_position('INFY', 'NSE', 'CNC', 'test_auth_token')
    assert net_qty == '0'

@patch('app.web.broker.broker.finvasia.api.order_api.get_positions')
@patch('app.web.broker.broker.finvasia.api.order_api.get_br_symbol')
def test_get_open_position_api_error(mock_get_br_symbol, mock_get_positions):
    mock_get_br_symbol.return_value = 'INFY'
    mock_get_positions.return_value = {'stat': 'Not_Ok', 'emsg': 'API error'}
    net_qty = get_open_position('INFY', 'NSE', 'CNC', 'test_auth_token')
    assert net_qty == '0'

@patch('app.web.broker.broker.finvasia.api.order_api.get_api_response')
def test_get_order_book_api_error(mock_get_api_response):
    mock_get_api_response.return_value = {'stat': 'Not_Ok', 'emsg': 'API error'}
    order_book = get_order_book('test_auth_token')
    assert order_book == []

@patch('app.web.broker.broker.finvasia.api.order_api.get_api_response')
def test_get_order_book_empty_response(mock_get_api_response):
    mock_get_api_response.return_value = []
    order_book = get_order_book('test_auth_token')
    assert order_book == []

@patch('app.web.broker.broker.finvasia.api.order_api.get_httpx_client')
@patch('app.web.broker.broker.finvasia.api.order_api.settings')
@patch('app.web.broker.broker.finvasia.api.order_api.get_token')
@patch('app.web.broker.broker.finvasia.api.order_api.transform_data')
def test_place_order_api_success(mock_transform_data, mock_get_token, mock_settings, mock_get_httpx_client):
    mock_settings.BROKER_API_KEY = 'test_api_key'
    mock_get_token.return_value = '12345'
    mock_transform_data.return_value = {'symbol': 'INFY', 'token': '12345', 'transformed': True}

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({'stat': 'Ok', 'norenordno': 'order_id_123'})
    mock_client.post.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    data = {'symbol': 'INFY', 'exchange': 'NSE', 'action': 'BUY', 'quantity': '10'}
    response, response_data, order_id = place_order_api(data, 'test_auth_token')

    assert response.status_code == 200
    assert response_data['stat'] == 'Ok'
    assert order_id == 'order_id_123'
    mock_client.post.assert_called_once()
    mock_transform_data.assert_called_once()

@patch('app.web.broker.broker.finvasia.api.order_api.get_httpx_client')
@patch('app.web.broker.broker.finvasia.api.order_api.settings')
@patch('app.web.broker.broker.finvasia.api.order_api.get_token')
@patch('app.web.broker.broker.finvasia.api.order_api.transform_data')
def test_place_order_api_failure(mock_transform_data, mock_get_token, mock_settings, mock_get_httpx_client):
    mock_settings.BROKER_API_KEY = 'test_api_key'
    mock_get_token.return_value = '12345'
    mock_transform_data.return_value = {'symbol': 'INFY', 'token': '12345', 'transformed': True}

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({'stat': 'Not_Ok', 'emsg': 'Order placement failed'})
    mock_client.post.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    data = {'symbol': 'INFY', 'exchange': 'NSE', 'action': 'BUY', 'quantity': '10'}
    response, response_data, order_id = place_order_api(data, 'test_auth_token')

    assert response.status_code == 200
    assert response_data['stat'] == 'Not_Ok'
    assert order_id is None

@patch('app.web.broker.broker.finvasia.api.order_api.get_open_position')
@patch('app.web.broker.broker.finvasia.api.order_api.place_order_api')
@patch('app.web.broker.broker.finvasia.api.order_api.map_product_type')
def test_place_smartorder_api_new_order(mock_map_product_type, mock_place_order_api, mock_get_open_position):
    mock_get_open_position.return_value = '0'
    mock_place_order_api.return_value = (MagicMock(status_code=200), {'stat': 'Ok', 'norenordno': 'smart_order_1'}, 'smart_order_1')
    mock_map_product_type.return_value = 'CNC'

    data = {'symbol': 'INFY', 'exchange': 'NSE', 'action': 'BUY', 'quantity': '10', 'product': 'CNC', 'position_size': '0'}
    response, response_data, order_id = place_smartorder_api(data, 'test_auth_token')

    assert order_id == 'smart_order_1'
    mock_place_order_api.assert_called_once()

@patch('app.web.broker.broker.finvasia.api.order_api.get_positions')
@patch('app.web.broker.broker.finvasia.api.order_api.get_symbol')
@patch('app.web.broker.broker.finvasia.api.order_api.place_order_api')
@patch('app.web.broker.broker.finvasia.api.order_api.reverse_map_product_type')
def test_close_all_positions_success(mock_reverse_map_product_type, mock_place_order_api, mock_get_symbol, mock_get_positions):
    mock_get_positions.return_value = [
        {'tsym': 'INFY', 'exch': 'NSE', 'prd': 'CNC', 'netqty': '10', 'token': '12345'},
        {'tsym': 'RELIANCE', 'exch': 'NSE', 'prd': 'CNC', 'netqty': '-5', 'token': '67890'}
    ]
    mock_get_symbol.side_effect = ['INFY', 'RELIANCE']
    mock_place_order_api.return_value = (MagicMock(status_code=200), {'stat': 'Ok', 'norenordno': 'sq_order_1'}, 'sq_order_1')
    mock_reverse_map_product_type.return_value = 'CNC'

    response, status_code = close_all_positions('test_api_key', 'test_auth_token')
    assert status_code == 200
    assert response['message'] == 'All Open Positions SquaredOff'
    assert mock_place_order_api.call_count == 2

@patch('app.web.broker.broker.finvasia.api.order_api.get_httpx_client')
@patch('app.web.broker.broker.finvasia.api.order_api.settings')
def test_cancel_order_success(mock_settings, mock_get_httpx_client):
    mock_settings.BROKER_API_KEY = 'test_api_key'
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({'stat': 'Ok'})
    mock_client.post.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    response, status_code = cancel_order('order_id_123', 'test_auth_token')
    assert status_code == 200
    assert response['status'] == 'success'
    assert response['orderid'] == 'order_id_123'

@patch('app.web.broker.broker.finvasia.api.order_api.get_httpx_client')
@patch('app.web.broker.broker.finvasia.api.order_api.settings')
@patch('app.web.broker.broker.finvasia.api.order_api.get_token')
@patch('app.web.broker.broker.finvasia.api.order_api.get_br_symbol')
@patch('app.web.broker.broker.finvasia.api.order_api.transform_modify_order_data')
def test_modify_order_success(mock_transform_modify_order_data, mock_get_br_symbol, mock_get_token, mock_settings, mock_get_httpx_client):
    mock_settings.BROKER_API_KEY = 'test_api_key'
    mock_get_token.return_value = '12345'
    mock_get_br_symbol.return_value = 'INFY'
    mock_transform_modify_order_data.return_value = {'orderid': 'mod_order_1', 'transformed_modify': True}

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({'stat': 'Ok'})
    mock_client.post.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    data = {'orderid': 'mod_order_1', 'symbol': 'INFY', 'exchange': 'NSE', 'quantity': '20'}
    response, status_code = modify_order(data, 'test_auth_token')

    assert status_code == 200
    assert response['status'] == 'success'
    assert response['orderid'] == 'mod_order_1'

@patch('app.web.broker.broker.finvasia.api.order_api.get_order_book')
@patch('app.web.broker.broker.finvasia.api.order_api.cancel_order')
def test_cancel_all_orders_api_success(mock_cancel_order, mock_get_order_book):
    mock_get_order_book.return_value = [
        {'norenordno': 'order1', 'status': 'OPEN'},
        {'norenordno': 'order2', 'status': 'TRIGGER PENDING'}
    ]
    mock_cancel_order.return_value = ({'status': 'success'}, 200)

    canceled_orders, failed_cancellations = cancel_all_orders_api({}, 'test_auth_token')

    assert not failed_cancellations
    assert len(canceled_orders) == 2
    assert mock_cancel_order.call_count == 2

@patch('app.web.broker.broker.finvasia.api.order_api.get_order_book')
def test_cancel_all_orders_api_no_orders(mock_get_order_book):
    mock_get_order_book.return_value = []

    canceled_orders, failed_cancellations = cancel_all_orders_api({}, 'test_auth_token')

    assert not failed_cancellations
    assert not canceled_orders

@patch('app.web.broker.broker.finvasia.api.order_api.get_order_book')
@patch('app.web.broker.broker.finvasia.api.order_api.cancel_order')
def test_cancel_all_orders_api_failure(mock_cancel_order, mock_get_order_book):
    mock_get_order_book.return_value = [
        {'norenordno': 'order1', 'status': 'OPEN'}
    ]
    mock_cancel_order.return_value = ({'status': 'error', 'message': 'Failed to cancel'}, 400)

    canceled_orders, failed_cancellations = cancel_all_orders_api({}, 'test_auth_token')

    assert not canceled_orders
    assert len(failed_cancellations) == 1