import pytest
from unittest.mock import MagicMock, patch
import json
import pandas as pd
from datetime import datetime, timedelta

# Import the functions and classes to be tested
from app.web.broker.broker.firstock.api.auth_api import authenticate_broker, sha256_hash
from app.web.broker.broker.firstock.api.data import BrokerData, get_api_response as get_data_api_response
from app.web.broker.broker.firstock.api.order_api import (
    get_order_book, get_trade_book, get_positions, get_holdings,
    get_open_position, place_order_api, place_smartorder_api,
    close_all_positions, cancel_order, modify_order, cancel_all_orders_api
)

# Fixtures for mocking dependencies
@pytest.fixture
def mock_settings():
    with patch('app.core.config.settings') as mock_settings:
        mock_settings.BROKER_API_SECRET = 'test_secret' # This should be the apiKey
        mock_settings.BROKER_API_KEY = 'test_api_key_1234' # This should be the vendorCode + userId
        yield mock_settings

@pytest.fixture
def mock_httpx_client():
    with patch('app.utils.httpx_client.get_httpx_client') as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_token_db():
    with patch('app.db.token_db.get_br_symbol') as mock_get_br_symbol, \
         patch('app.db.token_db.get_token') as mock_get_token, \
         patch('app.db.token_db.get_symbol') as mock_get_symbol:
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
    with patch('app.web.broker.broker.firstock.mapping.transform_data.transform_data') as mock_transform_data, \
         patch('app.web.broker.broker.firstock.mapping.transform_data.transform_modify_order_data') as mock_transform_modify_order_data, \
         patch('app.web.broker.broker.firstock.mapping.transform_data.map_product_type') as mock_map_product_type, \
         patch('app.web.broker.broker.firstock.mapping.transform_data.reverse_map_product_type') as mock_reverse_map_product_type:
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

@patch('app.web.broker.broker.firstock.api.auth_api.get_httpx_client')
@patch('app.web.broker.broker.firstock.api.auth_api.settings')
def test_authenticate_broker_success(mock_settings, mock_get_httpx_client):
    mock_settings.BROKER_API_SECRET = 'test_api_key'
    mock_settings.BROKER_API_KEY = 'test_vendor_code'

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'status': 'success', 'data': {'susertoken': 'mock_token_123'}}
    mock_client.post.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    token, error = authenticate_broker('user1', 'pass1', '123456')
    assert token == 'mock_token_123'
    assert error is None
    mock_client.post.assert_called_once()

@patch('app.web.broker.broker.firstock.api.auth_api.get_httpx_client')
@patch('app.web.broker.broker.firstock.api.auth_api.settings')
def test_authenticate_broker_failure_api_error(mock_settings, mock_get_httpx_client):
    mock_settings.BROKER_API_SECRET = 'test_api_key'
    mock_settings.BROKER_API_KEY = 'test_vendor_code'

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'status': 'error', 'message': 'Invalid credentials', 'error': {'message': 'Invalid credentials'}}
    mock_client.post.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    token, error = authenticate_broker('user1', 'wrong_pass', '123456')
    assert token is None
    assert error == 'Invalid credentials'
    mock_client.post.assert_called_once()

@patch('app.web.broker.broker.firstock.api.auth_api.get_httpx_client')
@patch('app.web.broker.broker.firstock.api.auth_api.settings')
def test_authenticate_broker_failure_http_error(mock_settings, mock_get_httpx_client):
    mock_settings.BROKER_API_SECRET = 'test_api_key'
    mock_settings.BROKER_API_KEY = 'test_vendor_code'

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = 'Bad Request'
    mock_client.post.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    token, error = authenticate_broker('user1', 'pass1', '123456')
    assert token is None
    assert error == 'Bad Request: Bad request - check required fields'
    mock_client.post.assert_called_once()

@patch('app.web.broker.broker.firstock.api.auth_api.get_httpx_client')
@patch('app.web.broker.broker.firstock.api.auth_api.settings')
def test_authenticate_broker_exception(mock_settings, mock_get_httpx_client):
    mock_settings.BROKER_API_SECRET = 'test_api_key'
    mock_settings.BROKER_API_KEY = 'test_vendor_code'

    mock_client = MagicMock()
    mock_client.post.side_effect = Exception("Network error")
    mock_get_httpx_client.return_value = mock_client

    token, error = authenticate_broker('user1', 'pass1', '123456')
    assert token is None
    assert error == 'Unexpected error: Network error'
    mock_client.post.assert_called_once()


# Tests for data.py
@patch('app.web.broker.broker.firstock.api.data.get_httpx_client')
@patch('app.web.broker.broker.firstock.api.data.settings')
@patch('app.web.broker.broker.firstock.api.data.logger')
def test_get_data_api_response_success(mock_logger, mock_settings, mock_get_httpx_client):
    mock_settings.BROKER_API_KEY = 'test_api_key_1234' # userId
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({'status': 'success', 'data': {'key': 'value'}})
    mock_client.request.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    response = get_data_api_response("/getQuote", "test_auth_token")
    assert response == {'status': 'success', 'data': {'key': 'value'}}
    mock_client.request.assert_called_once()
    mock_logger.info.assert_called() # Check that logger.info was called

@patch('app.web.broker.broker.firstock.api.data.get_httpx_client')
@patch('app.web.broker.broker.firstock.api.data.settings')
@patch('app.web.broker.broker.firstock.api.data.logger')
def test_get_data_api_response_json_decode_error(mock_logger, mock_settings, mock_get_httpx_client):
    mock_settings.BROKER_API_KEY = 'test_api_key_1234' # userId
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "invalid json"
    mock_client.request.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    response = get_data_api_response("/getQuote", "test_auth_token")
    assert response == {"status": "error", "message": "Empty response from server"} # Firstock handles JSONDecodeError by returning empty response
    mock_logger.error.assert_called_once() # Check that logger.error was called

@patch('app.web.broker.broker.firstock.api.data.get_api_response')
@patch('app.web.broker.broker.firstock.api.data.get_br_symbol')
def test_broker_data_get_quotes_success(mock_get_br_symbol, mock_get_api_response):
    mock_get_br_symbol.return_value = 'INFY-EQ'
    mock_get_api_response.return_value = {
        'status': 'success',
        'data': {
            'bestSellPrice1': 10.0, 'bestBuyPrice1': 11.0, 'dayHighPrice': 12.0,
            'dayLowPrice': 8.0, 'lastTradedPrice': 10.5, 'dayOpenPrice': 9.0,
            'dayClosePrice': 9.5, 'volume': 1000, 'openInterest': 500.0
        }
    }
    broker_data = BrokerData("test_auth_token")
    quotes = broker_data.get_quotes("INFY", "NSE")
    assert quotes['ltp'] == 10.5
    assert quotes['oi'] == 500
    mock_get_br_symbol.assert_called_once_with("INFY", "NSE")
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.data.get_api_response')
@patch('app.web.broker.broker.firstock.api.data.get_br_symbol')
def test_broker_data_get_quotes_api_error(mock_get_br_symbol, mock_get_api_response):
    mock_get_br_symbol.return_value = 'INVALID-SYMBOL'
    mock_get_api_response.return_value = {'status': 'error', 'error': {'message': 'Invalid symbol'}}
    broker_data = BrokerData("test_auth_token")
    quotes = broker_data.get_quotes("INVALID", "NSE")
    assert quotes['status'] == 'error'
    assert "Invalid symbol" in quotes['message']
    mock_get_br_symbol.assert_called_once_with("INVALID", "NSE")
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.data.get_api_response')
@patch('app.web.broker.broker.firstock.api.data.get_br_symbol')
def test_broker_data_get_depth_success(mock_get_br_symbol, mock_get_api_response):
    mock_get_br_symbol.return_value = 'INFY-EQ'
    mock_get_api_response.return_value = {
        'status': 'success',
        'data': {
            'bestBuyPrice1': 10.0, 'bestBuyQuantity1': 100,
            'bestSellPrice1': 11.0, 'bestSellQuantity1': 50,
            'dayHighPrice': 12.0, 'dayLowPrice': 8.0, 'lastTradedPrice': 10.5,
            'lastTradedQuantity': 10, 'openInterest': 500.0, 'dayOpenPrice': 9.0,
            'dayClosePrice': 9.5, 'totalBuyQuantity': 200, 'totalSellQuantity': 150, 'volume': 1000
        }
    }
    broker_data = BrokerData("test_auth_token")
    depth = broker_data.get_depth("INFY", "NSE")
    assert depth['ltp'] == 10.5
    assert depth['totalbuyqty'] == 200
    assert depth['totalsellqty'] == 150
    assert len(depth['bids']) == 1 # Only one bid in mock
    assert len(depth['asks']) == 1 # Only one ask in mock
    mock_get_br_symbol.assert_called_once_with("INFY", "NSE")
    mock_get_api_response.assert_called_once()


@patch('app.web.broker.broker.firstock.api.data.get_api_response')
@patch('app.web.broker.broker.firstock.api.data.get_br_symbol')
def test_broker_data_get_single_history_chunk_success(mock_get_br_symbol, mock_get_api_response):
    mock_get_br_symbol.return_value = 'INFY-EQ'
    mock_get_api_response.return_value = {
        'status': 'success',
        'data': [
            {'time': '2023-01-01', 'open': 100.0, 'high': 105.0, 'low': 99.0, 'close': 104.0, 'volume': 1000},
            {'time': '2023-01-02', 'open': 104.0, 'high': 108.0, 'low': 103.0, 'close': 107.0, 'volume': 1200}
        ]
    }
    broker_data = BrokerData("test_auth_token")
    df = broker_data._get_single_history_chunk("INFY", "NSE", "2023-01-01", "2023-01-02", "1day")
    assert not df.empty
    assert len(df) == 2
    assert df.iloc[0]['open'] == 100.0
    assert df.iloc[1]['close'] == 107.0
    mock_get_br_symbol.assert_called_once_with("INFY", "NSE")
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.data.get_api_response')
@patch('app.web.broker.broker.firstock.api.data.get_br_symbol')
def test_broker_data_get_single_history_chunk_api_error(mock_get_br_symbol, mock_get_api_response):
    mock_get_br_symbol.return_value = 'INVALID-SYMBOL'
    mock_get_api_response.return_value = {'status': 'error', 'error': {'message': 'Invalid symbol'}}
    broker_data = BrokerData("test_auth_token")
    df = broker_data._get_single_history_chunk("INVALID", "NSE", "2023-01-01", "2023-01-02", "1day")
    assert df.empty
    mock_get_br_symbol.assert_called_once_with("INVALID", "NSE")
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.data.datetime')
@patch('app.web.broker.broker.firstock.api.data.BrokerData._get_single_history_chunk')
def test_broker_data_get_history_multiple_chunks(mock_get_single_history_chunk, mock_datetime):
    # Mock datetime to control the current date
    mock_datetime.now.return_value = datetime(2023, 1, 30)
    mock_datetime.strptime.side_effect = lambda date_string, format: datetime.strptime(date_string, format)
    mock_datetime.strftime.side_effect = lambda date_obj, format: date_obj.strftime(format)
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
    mock_datetime.timedelta = timedelta

    # Mock _get_single_history_chunk to return data for two chunks
    mock_get_single_history_chunk.side_effect = [
        pd.DataFrame([
            {'time': '2023-01-01', 'open': 100.0, 'high': 105.0, 'low': 99.0, 'close': 104.0, 'volume': 1000},
            {'time': '2023-01-02', 'open': 104.0, 'high': 108.0, 'low': 103.0, 'close': 107.0, 'volume': 1200}
        ]),
        pd.DataFrame([
            {'time': '2023-01-03', 'open': 107.0, 'high': 110.0, 'low': 106.0, 'close': 109.0, 'volume': 1500},
            {'time': '2023-01-04', 'open': 109.0, 'high': 112.0, 'low': 108.0, 'close': 111.0, 'volume': 1300}
        ])
    ]

    broker_data = BrokerData("test_auth_token")
    df = broker_data.get_history("INFY", "NSE", "2023-01-01", "2023-01-04", "1day")
    assert not df.empty
    assert len(df) == 4
    assert mock_get_single_history_chunk.call_count == 2
    assert df.iloc[3]['close'] == 111.0

@patch('app.web.broker.broker.firstock.api.data.datetime')
@patch('app.web.broker.broker.firstock.api.data.BrokerData._get_single_history_chunk')
def test_broker_data_get_history_empty_response(mock_get_single_history_chunk, mock_datetime):
    mock_datetime.now.return_value = datetime(2023, 1, 30)
    mock_datetime.strptime.side_effect = lambda date_string, format: datetime.strptime(date_string, format)
    mock_datetime.strftime.side_effect = lambda date_obj, format: date_obj.strftime(format)
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
    mock_datetime.timedelta = timedelta

    mock_get_single_history_chunk.return_value = pd.DataFrame()

    broker_data = BrokerData("test_auth_token")
    df = broker_data.get_history("INFY", "NSE", "2023-01-01", "2023-01-04", "1day")
    assert df.empty
    assert mock_get_single_history_chunk.call_count == 1 # Only one call should be made if first chunk is empty


# Tests for order_api.py
@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
@patch('app.web.broker.broker.firstock.api.order_api.transform_data.reverse_map_product_type')
def test_get_order_book_success(mock_reverse_map_product_type, mock_get_api_response):
    mock_reverse_map_product_type.return_value = "MIS"
    mock_get_api_response.return_value = {
        'status': 'success',
        'data': [
            {'orderId': '1', 'instrumentName': 'INFY', 'exchange': 'NSE', 'productType': 'MIS', 'quantity': 10, 'price': 100.0, 'orderStatus': 'COMPLETE'}
        ]
    }
    order_book = get_order_book("test_auth_token")
    assert order_book[0]['order_id'] == '1'
    assert order_book[0]['qty'] == 10
    assert order_book[0]['product'] == 'MIS'
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
def test_get_order_book_api_error(mock_get_api_response):
    mock_get_api_response.return_value = {'status': 'error', 'error': {'message': 'No orders'}}
    order_book = get_order_book("test_auth_token")
    assert order_book == []
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
@patch('app.web.broker.broker.firstock.api.order_api.transform_data.reverse_map_product_type')
def test_get_trade_book_success(mock_reverse_map_product_type, mock_get_api_response):
    mock_reverse_map_product_type.return_value = "CNC"
    mock_get_api_response.return_value = {
        'status': 'success',
        'data': [
            {'tradeId': 'T1', 'instrumentName': 'TCS', 'exchange': 'NSE', 'productType': 'CNC', 'quantity': 5, 'price': 2000.0}
        ]
    }
    trade_book = get_trade_book("test_auth_token")
    assert trade_book[0]['trade_id'] == 'T1'
    assert trade_book[0]['qty'] == 5
    assert trade_book[0]['product'] == 'CNC'
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
def test_get_trade_book_api_error(mock_get_api_response):
    mock_get_api_response.return_value = {'status': 'error', 'error': {'message': 'No trades'}}
    trade_book = get_trade_book("test_auth_token")
    assert trade_book == []
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
@patch('app.web.broker.broker.firstock.api.order_api.transform_data.reverse_map_product_type')
def test_get_positions_success(mock_reverse_map_product_type, mock_get_api_response):
    mock_reverse_map_product_type.return_value = "MIS"
    mock_get_api_response.return_value = {
        'status': 'success',
        'data': [
            {'symbol': 'RELIANCE', 'exchange': 'NSE', 'productType': 'MIS', 'buyQuantity': 10, 'sellQuantity': 5, 'netQuantity': 5}
        ]
    }
    positions = get_positions("test_auth_token")
    assert positions[0]['symbol'] == 'RELIANCE'
    assert positions[0]['net_qty'] == 5
    assert positions[0]['product'] == 'MIS'
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
def test_get_positions_api_error(mock_get_api_response):
    mock_get_api_response.return_value = {'status': 'error', 'error': {'message': 'No positions'}}
    positions = get_positions("test_auth_token")
    assert positions == []
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
@patch('app.web.broker.broker.firstock.api.order_api.transform_data.reverse_map_product_type')
def test_get_holdings_success(mock_reverse_map_product_type, mock_get_api_response):
    mock_reverse_map_product_type.return_value = "CNC"
    mock_get_api_response.return_value = {
        'status': 'success',
        'data': [
            {'instrumentName': 'SBIN', 'exchange': 'NSE', 'productType': 'CNC', 'quantity': 20, 'avgPrice': 500.0}
        ]
    }
    holdings = get_holdings("test_auth_token")
    assert holdings[0]['symbol'] == 'SBIN'
    assert holdings[0]['qty'] == 20
    assert holdings[0]['product'] == 'CNC'
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
def test_get_holdings_api_error(mock_get_api_response):
    mock_get_api_response.return_value = {'status': 'error', 'error': {'message': 'No holdings'}}
    holdings = get_holdings("test_auth_token")
    assert holdings == []
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
@patch('app.web.broker.broker.firstock.api.order_api.transform_data.reverse_map_product_type')
def test_get_open_position_success(mock_reverse_map_product_type, mock_get_api_response):
    mock_reverse_map_product_type.return_value = "MIS"
    mock_get_api_response.return_value = {
        'status': 'success',
        'data': [
            {'symbol': 'RELIANCE', 'exchange': 'NSE', 'productType': 'MIS', 'buyQuantity': 10, 'sellQuantity': 5, 'netQuantity': 5}
        ]
    }
    open_positions = get_open_position("test_auth_token")
    assert open_positions[0]['symbol'] == 'RELIANCE'
    assert open_positions[0]['net_qty'] == 5
    assert open_positions[0]['product'] == 'MIS'
    mock_get_api_response.assert_called_once()


@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
@patch('app.web.broker.broker.firstock.api.order_api.transform_data.transform_data')
@patch('app.web.broker.broker.firstock.api.order_api.get_br_symbol')
def test_place_order_api_success(mock_get_br_symbol, mock_transform_data, mock_get_api_response):
    mock_get_br_symbol.return_value = 'INFY-EQ'
    mock_transform_data.return_value = {'symbol': 'INFY-EQ', 'price': 100}
    mock_get_api_response.return_value = {'status': 'success', 'data': {'orderId': 'ORD123'}}

    order_data = {'symbol': 'INFY', 'exchange': 'NSE', 'qty': 10, 'price': 100, 'type': 'BUY'}
    response, error, order_id = place_order_api(order_data, 'test_auth_token')
    assert response['status'] == 'success'
    assert order_id == 'ORD123'
    assert error is None
    mock_get_br_symbol.assert_called_once_with('INFY', 'NSE')
    mock_transform_data.assert_called_once()
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
@patch('app.web.broker.broker.firstock.api.order_api.transform_data.transform_data')
@patch('app.web.broker.broker.firstock.api.order_api.get_br_symbol')
def test_place_order_api_failure(mock_get_br_symbol, mock_transform_data, mock_get_api_response):
    mock_get_br_symbol.return_value = 'INFY-EQ'
    mock_transform_data.return_value = {'symbol': 'INFY-EQ', 'price': 100}
    mock_get_api_response.return_value = {'status': 'error', 'message': 'Invalid order'}

    order_data = {'symbol': 'INFY', 'exchange': 'NSE', 'qty': 10, 'price': 100, 'type': 'BUY'}
    response, error, order_id = place_order_api(order_data, 'test_auth_token')
    assert response['status'] == 'error'
    assert error == 'Invalid order'
    assert order_id is None
    mock_get_br_symbol.assert_called_once_with('INFY', 'NSE')
    mock_transform_data.assert_called_once()
    mock_get_api_response.assert_called_once()


@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
@patch('app.web.broker.broker.firstock.api.order_api.transform_data.transform_data')
@patch('app.web.broker.broker.firstock.api.order_api.get_br_symbol')
def test_place_smartorder_api_success(mock_get_br_symbol, mock_transform_data, mock_get_api_response):
    mock_get_br_symbol.return_value = 'INFY-EQ'
    mock_transform_data.return_value = {'symbol': 'INFY-EQ', 'price': 100}
    mock_get_api_response.return_value = {'status': 'success', 'data': {'orderId': 'ORD456'}}

    order_data = {'symbol': 'INFY', 'exchange': 'NSE', 'qty': 10, 'price': 100, 'type': 'BUY'}
    response, error, order_id = place_smartorder_api(order_data, 'test_auth_token')
    assert response['status'] == 'success'
    assert order_id == 'ORD456'
    assert error is None
    mock_get_br_symbol.assert_called_once_with('INFY', 'NSE')
    mock_transform_data.assert_called_once()
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
@patch('app.web.broker.broker.firstock.api.order_api.get_positions')
def test_close_all_positions_success(mock_get_positions, mock_get_api_response):
    mock_get_positions.return_value = [
        {'symbol': 'INFY', 'exchange': 'NSE', 'net_qty': 10, 'product': 'CNC', 'token': '1234'},
        {'symbol': 'TCS', 'exchange': 'NSE', 'net_qty': -5, 'product': 'MIS', 'token': '5678'}
    ]
    mock_get_api_response.return_value = {'status': 'success'}

    response, error = close_all_positions('test_auth_token')
    assert response['status'] == 'success'
    assert error is None
    assert mock_get_api_response.call_count == 2 # One for each position
    mock_get_positions.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
def test_cancel_order_success(mock_get_api_response):
    mock_get_api_response.return_value = {'status': 'success'}

    response, error = cancel_order('ORD123', 'test_auth_token')
    assert response['status'] == 'success'
    assert error is None
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
@patch('app.web.broker.broker.firstock.api.order_api.transform_data.transform_modify_order_data')
def test_modify_order_success(mock_transform_modify_order_data, mock_get_api_response):
    mock_transform_modify_order_data.return_value = {'orderId': 'ORD123', 'price': 105}
    mock_get_api_response.return_value = {'status': 'success'}

    order_data = {'order_id': 'ORD123', 'price': 105}
    response, error = modify_order(order_data, 'test_auth_token')
    assert response['status'] == 'success'
    assert error is None
    mock_transform_modify_order_data.assert_called_once()
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
@patch('app.web.broker.broker.firstock.api.order_api.get_order_book')
def test_cancel_all_orders_api_success(mock_get_order_book, mock_get_api_response):
    mock_get_order_book.return_value = [
        {'order_id': 'ORD1', 'status': 'PENDING'},
        {'order_id': 'ORD2', 'status': 'PENDING'}
    ]
    mock_get_api_response.return_value = {'status': 'success'}

    response, error = cancel_all_orders_api('test_auth_token')
    assert response['status'] == 'success'
    assert error is None
    assert mock_get_api_response.call_count == 2 # One for each pending order
    mock_get_order_book.assert_called_once()


@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
@patch('app.web.broker.broker.firstock.api.order_api.transform_data.transform_data')
@patch('app.web.broker.broker.firstock.api.order_api.get_br_symbol')
def test_place_order_api_success(mock_get_br_symbol, mock_transform_data, mock_get_api_response):
    mock_get_br_symbol.return_value = 'INFY-EQ'
    mock_transform_data.return_value = {'symbol': 'INFY-EQ', 'price': 100}
    mock_get_api_response.return_value = {'status': 'success', 'data': {'orderId': 'ORD123'}}

    order_data = {'symbol': 'INFY', 'exchange': 'NSE', 'qty': 10, 'price': 100, 'type': 'BUY'}
    response, error, order_id = place_order_api(order_data, 'test_auth_token')
    assert response['status'] == 'success'
    assert order_id == 'ORD123'
    assert error is None
    mock_get_br_symbol.assert_called_once_with('INFY', 'NSE')
    mock_transform_data.assert_called_once()
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
@patch('app.web.broker.broker.firstock.api.order_api.transform_data.transform_data')
@patch('app.web.broker.broker.firstock.api.order_api.get_br_symbol')
def test_place_order_api_failure(mock_get_br_symbol, mock_transform_data, mock_get_api_response):
    mock_get_br_symbol.return_value = 'INFY-EQ'
    mock_transform_data.return_value = {'symbol': 'INFY-EQ', 'price': 100}
    mock_get_api_response.return_value = {'status': 'error', 'message': 'Invalid order'}

    order_data = {'symbol': 'INFY', 'exchange': 'NSE', 'qty': 10, 'price': 100, 'type': 'BUY'}
    response, error, order_id = place_order_api(order_data, 'test_auth_token')
    assert response['status'] == 'error'
    assert error == 'Invalid order'
    assert order_id is None
    mock_get_br_symbol.assert_called_once_with('INFY', 'NSE')
    mock_transform_data.assert_called_once()
    mock_get_api_response.assert_called_once()


@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
@patch('app.web.broker.broker.firstock.api.order_api.transform_data.transform_data')
@patch('app.web.broker.broker.firstock.api.order_api.get_br_symbol')
def test_place_smartorder_api_success(mock_get_br_symbol, mock_transform_data, mock_get_api_response):
    mock_get_br_symbol.return_value = 'INFY-EQ'
    mock_transform_data.return_value = {'symbol': 'INFY-EQ', 'price': 100}
    mock_get_api_response.return_value = {'status': 'success', 'data': {'orderId': 'ORD456'}}

    order_data = {'symbol': 'INFY', 'exchange': 'NSE', 'qty': 10, 'price': 100, 'type': 'BUY'}
    response, error, order_id = place_smartorder_api(order_data, 'test_auth_token')
    assert response['status'] == 'success'
    assert order_id == 'ORD456'
    assert error is None
    mock_get_br_symbol.assert_called_once_with('INFY', 'NSE')
    mock_transform_data.assert_called_once()
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
@patch('app.web.broker.broker.firstock.api.order_api.get_positions')
def test_close_all_positions_success(mock_get_positions, mock_get_api_response):
    mock_get_positions.return_value = [
        {'symbol': 'INFY', 'exchange': 'NSE', 'net_qty': 10, 'product': 'CNC', 'token': '1234'},
        {'symbol': 'TCS', 'exchange': 'NSE', 'net_qty': -5, 'product': 'MIS', 'token': '5678'}
    ]
    mock_get_api_response.return_value = {'status': 'success'}

    response, error = close_all_positions('test_auth_token')
    assert response['status'] == 'success'
    assert error is None
    assert mock_get_api_response.call_count == 2 # One for each position
    mock_get_positions.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
def test_cancel_order_success(mock_get_api_response):
    mock_get_api_response.return_value = {'status': 'success'}

    response, error = cancel_order('ORD123', 'test_auth_token')
    assert response['status'] == 'success'
    assert error is None
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
@patch('app.web.broker.broker.firstock.api.order_api.transform_data.transform_modify_order_data')
def test_modify_order_success(mock_transform_modify_order_data, mock_get_api_response):
    mock_transform_modify_order_data.return_value = {'orderId': 'ORD123', 'price': 105}
    mock_get_api_response.return_value = {'status': 'success'}

    order_data = {'order_id': 'ORD123', 'price': 105}
    response, error = modify_order(order_data, 'test_auth_token')
    assert response['status'] == 'success'
    assert error is None
    mock_transform_modify_order_data.assert_called_once()
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
@patch('app.web.broker.broker.firstock.api.order_api.get_order_book')
def test_cancel_all_orders_api_success(mock_get_order_book, mock_get_api_response):
    mock_get_order_book.return_value = [
        {'order_id': 'ORD1', 'status': 'PENDING'},
        {'order_id': 'ORD2', 'status': 'PENDING'}
    ]
    mock_get_api_response.return_value = {'status': 'success'}

    response, error = cancel_all_orders_api('test_auth_token')
    assert response['status'] == 'success'
    assert error is None
    assert mock_get_api_response.call_count == 2 # One for each pending order
    mock_get_order_book.assert_called_once()

@patch('app.web.broker.broker.firstock.api.order_api.get_api_response')
def test_get_open_position_api_error(mock_get_api_response):
    mock_get_api_response.return_value = {'status': 'error', 'error': {'message': 'No open positions'}}
    open_positions = get_open_position("test_auth_token")
    assert open_positions == []
    mock_get_api_response.assert_called_once()


@patch('app.web.broker.broker.firstock.api.data.get_api_response')
@patch('app.web.broker.broker.firstock.api.data.get_br_symbol')
def test_broker_data_get_history_chunked_success(mock_get_br_symbol, mock_get_api_response):
    mock_get_br_symbol.return_value = 'INFY-EQ'
    mock_get_api_response.return_value = {
        'status': 'success',
        'data': [
            {'time': '2023-01-01', 'open': 100.0, 'high': 105.0, 'low': 99.0, 'close': 104.0, 'volume': 1000},
            {'time': '2023-01-02', 'open': 104.0, 'high': 108.0, 'low': 103.0, 'close': 107.0, 'volume': 1200}
        ]
    }
    broker_data = BrokerData("test_auth_token")
    df = broker_data._get_single_history_chunk("INFY", "NSE", "2023-01-01", "2023-01-02", "1day")
    assert not df.empty
    assert len(df) == 2
    assert df.iloc[0]['open'] == 100.0
    assert df.iloc[1]['close'] == 107.0
    mock_get_br_symbol.assert_called_once_with("INFY", "NSE")
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.data.get_api_response')
@patch('app.web.broker.broker.firstock.api.data.get_br_symbol')
def test_broker_data_get_history_chunked_api_error(mock_get_br_symbol, mock_get_api_response):
    mock_get_br_symbol.return_value = 'INVALID-SYMBOL'
    mock_get_api_response.return_value = {'status': 'error', 'error': {'message': 'Invalid symbol'}}
    broker_data = BrokerData("test_auth_token")
    df = broker_data._get_single_history_chunk("INVALID", "NSE", "2023-01-01", "2023-01-02", "1day")
    assert df.empty
    mock_get_br_symbol.assert_called_once_with("INVALID", "NSE")
    mock_get_api_response.assert_called_once()

@patch('app.web.broker.broker.firstock.api.data.datetime')
@patch('app.web.broker.broker.firstock.api.data.BrokerData._get_single_history_chunk')
def test_broker_data_get_history_multiple_chunks(mock_get_single_history_chunk, mock_datetime):
    # Mock datetime to control the current date
    mock_datetime.now.return_value = datetime(2023, 1, 30)
    mock_datetime.strptime.side_effect = lambda date_string, format: datetime.strptime(date_string, format)
    mock_datetime.strftime.side_effect = lambda date_obj, format: date_obj.strftime(format)
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
    mock_datetime.timedelta = timedelta

    # Mock _get_single_history_chunk to return data for two chunks
    mock_get_single_history_chunk.side_effect = [
        pd.DataFrame([
            {'time': '2023-01-01', 'open': 100.0, 'high': 105.0, 'low': 99.0, 'close': 104.0, 'volume': 1000},
            {'time': '2023-01-02', 'open': 104.0, 'high': 108.0, 'low': 103.0, 'close': 107.0, 'volume': 1200}
        ]),
        pd.DataFrame([
            {'time': '2023-01-03', 'open': 107.0, 'high': 110.0, 'low': 106.0, 'close': 109.0, 'volume': 1500},
            {'time': '2023-01-04', 'open': 109.0, 'high': 112.0, 'low': 108.0, 'close': 111.0, 'volume': 1300}
        ])
    ]

    broker_data = BrokerData("test_auth_token")
    df = broker_data.get_history("INFY", "NSE", "2023-01-01", "2023-01-04", "1day")
    assert not df.empty
    assert len(df) == 4
    assert mock_get_single_history_chunk.call_count == 2
    assert df.iloc[3]['close'] == 111.0

@patch('app.web.broker.broker.firstock.api.data.datetime')
@patch('app.web.broker.broker.firstock.api.data.BrokerData._get_single_history_chunk')
def test_broker_data_get_history_empty_response(mock_get_single_history_chunk, mock_datetime):
    mock_datetime.now.return_value = datetime(2023, 1, 30)
    mock_datetime.strptime.side_effect = lambda date_string, format: datetime.strptime(date_string, format)
    mock_datetime.strftime.side_effect = lambda date_obj, format: date_obj.strftime(format)
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
    mock_datetime.timedelta = timedelta

    mock_get_single_history_chunk.return_value = pd.DataFrame()

    broker_data = BrokerData("test_auth_token")
    df = broker_data.get_history("INFY", "NSE", "2023-01-01", "2023-01-04", "1day")
    assert df.empty
    assert mock_get_single_history_chunk.call_count == 1 # Only one call should be made if first chunk is empty

@patch('app.web.broker.broker.firstock.api.data.get_api_response')
@patch('app.web.broker.broker.firstock.api.data.get_br_symbol')
def test_broker_data_get_depth_api_error(mock_get_br_symbol, mock_get_api_response):
    mock_get_br_symbol.return_value = 'INVALID-SYMBOL'
    mock_get_api_response.return_value = {'status': 'error', 'error': {'message': 'Invalid symbol'}}
    broker_data = BrokerData("test_auth_token")
    depth = broker_data.get_depth("INVALID", "NSE")
    assert depth['status'] == 'error'
    assert "Invalid symbol" in depth['message']
    mock_get_br_symbol.assert_called_once_with("INVALID", "NSE")
    mock_get_api_response.assert_called_once()