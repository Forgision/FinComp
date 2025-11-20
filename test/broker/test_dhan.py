import pytest
pytest.skip("Skipped by user request", allow_module_level=True)
from unittest.mock import patch, MagicMock
import json

from app.web.brokers.dhan.api.auth_api import authenticate_broker
from app.web.brokers.dhan.api.order_api import get_order_details_api

class TestDhanIntegration:
    def setUp(self):
        self.auth_token = "dummy_auth_token"

        # Mock settings for API keys
        patcher_api_key = patch('app.core.config.settings.BROKER_API_KEY', "test_api_key")
        patcher_api_secret = patch('app.core.config.settings.BROKER_API_SECRET', "test_api_secret")
        
        self.mock_api_key = patcher_api_key.start()
        self.mock_api_secret = patcher_api_secret.start()
        
        self.addCleanup(patcher_api_key.stop)
        self.addCleanup(patcher_api_secret.stop)

    @patch('app.web.broker.broker.dhan.api.auth_api.settings')
    def test_authenticate_broker_success(self, mock_settings):
        mock_settings.BROKER_API_SECRET = "mock_secret"
        auth_string, error = authenticate_broker("dummy_code")
        self.assertEqual(auth_string, "mock_secret")
        self.assertIsNone(error)

    @patch('app.web.broker.broker.dhan.api.auth_api.settings')
    def test_authenticate_broker_exception(self, mock_settings):
        mock_settings.BROKER_API_SECRET = "mock_secret"
        with self.assertRaisesRegex(Exception, "Test exception"):
            authenticate_broker("dummy_code")


@patch('app.web.broker.broker.dhan.api.data.get_token')
@patch('app.web.broker.broker.dhan.api.data.BrokerData._get_exchange_segment')
@patch('app.web.broker.broker.dhan.api.data.get_api_response')
def test_get_history_daily_success(self, mock_get_api_response, mock_get_exchange_segment, mock_get_token):
    mock_get_token.return_value = "12345"
    mock_get_exchange_segment.return_value = "NSE_EQ"
    mock_get_api_response.return_value = {
        "data": {
            "history": [
                {"start_time": "2023-01-01 09:15:00", "end_time": "2023-01-01 15:30:00", "open": 100.0, "high": 105.0, "low": 98.0, "close": 103.0, "volume": 1000},
                {"start_time": "2023-01-02 09:15:00", "end_time": "2023-01-02 15:30:00", "open": 103.0, "high": 108.0, "low": 101.0, "close": 106.0, "volume": 1200}
            ]
        }
    }

    broker_data = BrokerData(self.auth_token)
    history_data = broker_data.get_history("SYMBOL", "NSE", "2023-01-01", "2023-01-02", "1D")

    self.assertEqual(len(history_data), 2)
    self.assertEqual(history_data[0]['open'], 100.0)
    self.assertEqual(history_data[1]['close'], 106.0)

@patch('app.web.broker.broker.dhan.api.data.get_token')
@patch('app.web.broker.broker.dhan.api.data.BrokerData._get_exchange_segment')
@patch('app.web.broker.broker.dhan.api.data.get_api_response')
def test_get_history_intraday_success(self, mock_get_api_response, mock_get_exchange_segment, mock_get_token):
    mock_get_token.return_value = "12345"
    mock_get_exchange_segment.return_value = "NSE_EQ"
    mock_get_api_response.return_value = {
        "data": {
            "history": [
                {"start_time": "2023-01-01 09:15:00", "end_time": "2023-01-01 09:30:00", "open": 100.0, "high": 100.5, "low": 99.8, "close": 100.3, "volume": 100},
                {"start_time": "2023-01-01 09:30:00", "end_time": "2023-01-01 09:45:00", "open": 100.3, "high": 101.0, "low": 100.2, "close": 100.8, "volume": 120}
            ]
        }
    }

    broker_data = BrokerData(self.auth_token)
    history_data = broker_data.get_history("SYMBOL", "NSE", "2023-01-01", "2023-01-01", "15m")

    self.assertEqual(len(history_data), 2)
    self.assertEqual(history_data[0]['open'], 100.0)
    self.assertEqual(history_data[1]['close'], 100.8)

@patch('app.web.broker.broker.dhan.api.data.get_token')
@patch('app.web.broker.broker.dhan.api.data.BrokerData._get_exchange_segment')
@patch('app.web.broker.broker.dhan.api.data.get_api_response')
def test_get_history_empty_data(self, mock_get_api_response, mock_get_exchange_segment, mock_get_token):
    mock_get_token.return_value = "12345"
    mock_get_exchange_segment.return_value = "NSE_EQ"
    mock_get_api_response.return_value = {"data": {"history": []}}

    broker_data = BrokerData(self.auth_token)
    history_data = broker_data.get_history("SYMBOL", "NSE", "2023-01-01", "2023-01-02", "1D")

    self.assertEqual(len(history_data), 0)

@patch('app.web.broker.broker.dhan.api.data.get_token')
@patch('app.web.broker.broker.dhan.api.data.BrokerData._get_exchange_segment')
@patch('app.web.broker.broker.dhan.api.data.get_api_response')
def test_get_history_general_exception(self, mock_get_api_response, mock_get_exchange_segment, mock_get_token):
    mock_get_token.return_value = "12345"
    mock_get_exchange_segment.return_value = "NSE_EQ"
    mock_get_api_response.side_effect = Exception("Some other error")

    broker_data = BrokerData(self.auth_token)
    with self.assertRaisesRegex(Exception, "Error fetching historical data: Some other error"):
        broker_data.get_history("SYMBOL", "NSE", "2023-01-01", "2023-01-02", "1D")



@patch('app.web.broker.broker.dhan.api.data.get_token')
@patch('app.web.broker.broker.dhan.api.data.BrokerData._get_exchange_segment')
@patch('app.web.broker.broker.dhan.api.data.get_api_response')
def test_get_quotes_success(self, mock_get_api_response, mock_get_exchange_segment, mock_get_token):
    mock_get_token.return_value = "12345"
    mock_get_exchange_segment.return_value = "NSE_EQ"
    mock_get_api_response.return_value = {
        "data": {
            "NSE_EQ": {
                "12345": {
                    "last_price": 100.50,
                    "ohlc": {"open": 99.0, "high": 101.0, "low": 98.0, "close": 99.5},
                    "volume": 1000,
                    "oi": 500,
                    "depth": {
                        "buy": [{"price": 100.45, "quantity": 100}],
                        "sell": [{"price": 100.55, "quantity": 100}]
                    }
                }
            }
        }
    }

    broker_data = BrokerData(self.auth_token)
    quotes = broker_data.get_quotes("SYMBOL", "NSE")

    self.assertEqual(quotes['ltp'], 100.50)
    self.assertEqual(quotes['open'], 99.0)
    self.assertEqual(quotes['high'], 101.0)
    self.assertEqual(quotes['low'], 98.0)
    self.assertEqual(quotes['volume'], 1000)
    self.assertEqual(quotes['oi'], 500)
    self.assertEqual(quotes['bid'], 100.45)
    self.assertEqual(quotes['ask'], 100.55)
    self.assertEqual(quotes['prev_close'], 99.5)

@patch('app.web.broker.broker.dhan.api.data.get_token')
@patch('app.web.broker.broker.dhan.api.data.BrokerData._get_exchange_segment')
@patch('app.web.broker.broker.dhan.api.data.get_api_response')
def test_get_quotes_empty_data(self, mock_get_api_response, mock_get_exchange_segment, mock_get_token):
    mock_get_token.return_value = "12345"
    mock_get_exchange_segment.return_value = "NSE_EQ"
    mock_get_api_response.return_value = {"data": {"NSE_EQ": {"12345": {}}}}

    broker_data = BrokerData(self.auth_token)
    quotes = broker_data.get_quotes("SYMBOL", "NSE")

    self.assertEqual(quotes['ltp'], 0)
    self.assertEqual(quotes['open'], 0)
    self.assertEqual(quotes['high'], 0)
    self.assertEqual(quotes['low'], 0)
    self.assertEqual(quotes['volume'], 0)
    self.assertEqual(quotes['oi'], 0)
    self.assertEqual(quotes['bid'], 0)
    self.assertEqual(quotes['ask'], 0)
    self.assertEqual(quotes['prev_close'], 0)

@patch('app.web.broker.broker.dhan.api.data.get_token')
@patch('app.web.broker.broker.dhan.api.data.BrokerData._get_exchange_segment')
@patch('app.web.broker.broker.dhan.api.data.get_api_response')
def test_get_quotes_market_data_subscription_error(self, mock_get_api_response, mock_get_exchange_segment, mock_get_token):
    mock_get_token.return_value = "12345"
    mock_get_exchange_segment.return_value = "NSE_EQ"
    mock_get_api_response.side_effect = Exception("Market data subscription required")

    broker_data = BrokerData(self.auth_token)
    quotes = broker_data.get_quotes("SYMBOL", "NSE")

    self.assertEqual(quotes['ltp'], 0)
    self.assertIn("Market data subscription required", quotes['error'])

@patch('app.web.broker.broker.dhan.api.data.get_token')
@patch('app.web.broker.broker.dhan.api.data.BrokerData._get_exchange_segment')
@patch('app.web.broker.broker.dhan.api.data.get_api_response')
def test_get_quotes_general_exception(self, mock_get_api_response, mock_get_exchange_segment, mock_get_token):
    mock_get_token.return_value = "12345"
    mock_get_exchange_segment.return_value = "NSE_EQ"
    mock_get_api_response.side_effect = Exception("Some other error")

    broker_data = BrokerData(self.auth_token)
    with self.assertRaisesRegex(Exception, "Error fetching quotes: Some other error"):
        broker_data.get_quotes("SYMBOL", "NSE")

# Order Management Tests
@patch('app.web.broker.broker.dhan.api.order_api.get_token')
@patch('app.web.broker.broker.dhan.api.order_api.transform_data')
@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_place_order_api_success(self, mock_get_httpx_client, mock_transform_data, mock_get_token):
    mock_get_token.return_value = "12345"
    mock_transform_data.return_value = {"tradingSymbol": "SYMBOL", "exchangeSegment": "NSE_EQ", "orderType": "MARKET"}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"orderId": "123456789"})
    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    order_data = {"symbol": "SYMBOL", "exchange": "NSE", "action": "BUY", "quantity": "1"}
    res, response_data, order_id = place_order_api(order_data, self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(response_data['orderId'], "123456789")
    self.assertEqual(order_id, "123456789")
    mock_get_token.assert_called_once_with("SYMBOL", "NSE")
    mock_transform_data.assert_called_once()
    mock_client.post.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_token')
@patch('app.web.broker.broker.dhan.api.order_api.transform_data')
@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_place_order_api_failure(self, mock_get_httpx_client, mock_transform_data, mock_get_token):
    mock_get_token.return_value = "12345"
    mock_transform_data.return_value = {"tradingSymbol": "SYMBOL", "exchangeSegment": "NSE_EQ", "orderType": "MARKET"}

    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = json.dumps({"status": "failed", "message": "Invalid order"})
    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    order_data = {"symbol": "SYMBOL", "exchange": "NSE", "action": "BUY", "quantity": "1"}
    res, response_data, order_id = place_order_api(order_data, self.auth_token)

    self.assertEqual(res.status_code, 400)
    self.assertEqual(response_data['status'], "failed")
    self.assertIsNone(order_id)

@patch('app.web.broker.broker.dhan.api.order_api.get_token')
@patch('app.web.broker.broker.dhan.api.order_api.transform_data')
@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_place_order_api_json_decode_error(self, mock_get_httpx_client, mock_transform_data, mock_get_token):
    mock_get_token.return_value = "12345"
    mock_transform_data.return_value = {"tradingSymbol": "SYMBOL", "exchangeSegment": "NSE_EQ", "orderType": "MARKET"}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "invalid json"
    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    order_data = {"symbol": "SYMBOL", "exchange": "NSE", "action": "BUY", "quantity": "1"}
    res, response_data, order_id = place_order_api(order_data, self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(response_data['error'], "Invalid JSON response")
    self.assertIsNone(order_id)

@patch('app.web.broker.broker.dhan.api.order_api.get_open_position')
@patch('app.web.broker.broker.dhan.api.order_api.place_order_api')
def test_place_smartorder_api_no_action_needed(self, mock_place_order_api, mock_get_open_position):
    mock_get_open_position.return_value = 10
    order_data = {"symbol": "SYMBOL", "exchange": "NSE", "product": "CNC", "position_size": "10", "quantity": "0"}
    res, response_data, order_id = place_smartorder_api(order_data, self.auth_token)

    self.assertIsNone(res)
    self.assertEqual(response_data['message'], "No action needed. Position size matches current position")
    self.assertIsNone(order_id)
    mock_place_order_api.assert_not_called()

@patch('app.web.broker.broker.dhan.api.order_api.get_open_position')
@patch('app.web.broker.broker.dhan.api.order_api.place_order_api')
def test_place_smartorder_api_buy_new_position(self, mock_place_order_api, mock_get_open_position):
    mock_get_open_position.return_value = 0
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"orderId": "123"})
    mock_place_order_api.return_value = (mock_response, {"orderId": "123"}, "123")

    order_data = {"symbol": "SYMBOL", "exchange": "NSE", "product": "CNC", "position_size": "5", "action": "BUY", "quantity": "5"}
    res, response_data, order_id = place_smartorder_api(order_data, self.auth_token)

    self.assertEqual(order_id, "123")
    mock_place_order_api.assert_called_once()
    self.assertEqual(mock_place_order_api.call_args[0][0]["quantity"], "5")
    self.assertEqual(mock_place_order_api.call_args[0][0]["action"], "BUY")

@patch('app.web.broker.broker.dhan.api.order_api.get_open_position')
@patch('app.web.broker.broker.dhan.api.order_api.place_order_api')
def test_place_smartorder_api_sell_new_position(self, mock_place_order_api, mock_get_open_position):
    mock_get_open_position.return_value = 0
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"orderId": "123"})
    mock_place_order_api.return_value = (mock_response, {"orderId": "123"}, "123")

    order_data = {"symbol": "SYMBOL", "exchange": "NSE", "product": "CNC", "position_size": "-5", "action": "SELL", "quantity": "5"}
    res, response_data, order_id = place_smartorder_api(order_data, self.auth_token)

    self.assertEqual(order_id, "123")
    mock_place_order_api.assert_called_once()
    self.assertEqual(mock_place_order_api.call_args[0][0]["quantity"], "5")
    self.assertEqual(mock_place_order_api.call_args[0][0]["action"], "SELL")

@patch('app.web.broker.broker.dhan.api.order_api.get_open_position')
@patch('app.web.broker.broker.dhan.api.order_api.place_order_api')
def test_place_smartorder_api_increase_long_position(self, mock_place_order_api, mock_get_open_position):
    mock_get_open_position.return_value = 5
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"orderId": "123"})
    mock_place_order_api.return_value = (mock_response, {"orderId": "123"}, "123")

    order_data = {"symbol": "SYMBOL", "exchange": "NSE", "product": "CNC", "position_size": "10", "action": "BUY", "quantity": "5"}
    res, response_data, order_id = place_smartorder_api(order_data, self.auth_token)

    self.assertEqual(order_id, "123")
    mock_place_order_api.assert_called_once()
    self.assertEqual(mock_place_order_api.call_args[0][0]["quantity"], "5")
    self.assertEqual(mock_place_order_api.call_args[0][0]["action"], "BUY")

@patch('app.web.broker.broker.dhan.api.order_api.get_open_position')
@patch('app.web.broker.broker.dhan.api.order_api.place_order_api')
def test_place_smartorder_api_decrease_long_position(self, mock_place_order_api, mock_get_open_position):
    mock_get_open_position.return_value = 10
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"orderId": "123"})
    mock_place_order_api.return_value = (mock_response, {"orderId": "123"}, "123")

    order_data = {"symbol": "SYMBOL", "exchange": "NSE", "product": "CNC", "position_size": "5", "action": "SELL", "quantity": "5"}
    res, response_data, order_id = place_smartorder_api(order_data, self.auth_token)

    self.assertEqual(order_id, "123")
    mock_place_order_api.assert_called_once()
    self.assertEqual(mock_place_order_api.call_args[0][0]["quantity"], "5")
    self.assertEqual(mock_place_order_api.call_args[0][0]["action"], "SELL")

@patch('app.web.broker.broker.dhan.api.order_api.get_open_position')
@patch('app.web.broker.broker.dhan.api.order_api.place_order_api')
def test_place_smartorder_api_square_off_long_position(self, mock_place_order_api, mock_get_open_position):
    mock_get_open_position.return_value = 10
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"orderId": "123"})
    mock_place_order_api.return_value = (mock_response, {"orderId": "123"}, "123")

    order_data = {"symbol": "SYMBOL", "exchange": "NSE", "product": "CNC", "position_size": "0", "action": "SELL", "quantity": "10"}
    res, response_data, order_id = place_smartorder_api(order_data, self.auth_token)

    self.assertEqual(order_id, "123")
    mock_place_order_api.assert_called_once()
    self.assertEqual(mock_place_order_api.call_args[0][0]["quantity"], "10")
    self.assertEqual(mock_place_order_api.call_args[0][0]["action"], "SELL")

@patch('app.web.broker.broker.dhan.api.order_api.get_open_position')
@patch('app.web.broker.broker.dhan.api.order_api.place_order_api')
def test_place_smartorder_api_square_off_short_position(self, mock_place_order_api, mock_get_open_position):
    mock_get_open_position.return_value = -10
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"orderId": "123"})
    mock_place_order_api.return_value = (mock_response, {"orderId": "123"}, "123")

    order_data = {"symbol": "SYMBOL", "exchange": "NSE", "product": "CNC", "position_size": "0", "action": "BUY", "quantity": "10"}
    res, response_data, order_id = place_smartorder_api(order_data, self.auth_token)

    self.assertEqual(order_id, "123")
    mock_place_order_api.assert_called_once()
    self.assertEqual(mock_place_order_api.call_args[0][0]["quantity"], "10")
    self.assertEqual(mock_place_order_api.call_args[0][0]["action"], "BUY")

@patch('app.web.broker.broker.dhan.api.order_api.get_open_position')
@patch('app.web.broker.broker.dhan.api.order_api.place_order_api')
def test_place_smartorder_api_reverse_long_to_short(self, mock_place_order_api, mock_get_open_position):
    mock_get_open_position.return_value = 5
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"orderId": "123"})
    mock_place_order_api.return_value = (mock_response, {"orderId": "123"}, "123")

    order_data = {"symbol": "SYMBOL", "exchange": "NSE", "product": "CNC", "position_size": "-5", "action": "SELL", "quantity": "10"}
    res, response_data, order_id = place_smartorder_api(order_data, self.auth_token)

    self.assertEqual(order_id, "123")
    mock_place_order_api.assert_called_once()
    self.assertEqual(mock_place_order_api.call_args[0][0]["quantity"], "10")
    self.assertEqual(mock_place_order_api.call_args[0][0]["action"], "SELL")

@patch('app.web.broker.broker.dhan.api.order_api.get_open_position')
@patch('app.web.broker.broker.dhan.api.order_api.place_order_api')
def test_place_smartorder_api_reverse_short_to_long(self, mock_place_order_api, mock_get_open_position):
    mock_get_open_position.return_value = -5
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"orderId": "123"})
    mock_place_order_api.return_value = (mock_response, {"orderId": "123"}, "123")

    order_data = {"symbol": "SYMBOL", "exchange": "NSE", "product": "CNC", "position_size": "5", "action": "BUY", "quantity": "10"}
    res, response_data, order_id = place_smartorder_api(order_data, self.auth_token)

    self.assertEqual(order_id, "123")
    mock_place_order_api.assert_called_once()
    self.assertEqual(mock_place_order_api.call_args[0][0]["quantity"], "10")
    self.assertEqual(mock_place_order_api.call_args[0][0]["action"], "BUY")

@patch('app.web.broker.broker.dhan.api.order_api.get_open_position')
@patch('app.web.broker.broker.dhan.api.order_api.place_order_api')
def test_place_smartorder_api_exception_in_place_order(self, mock_place_order_api, mock_get_open_position):
    mock_get_open_position.return_value = 0
    mock_place_order_api.side_effect = Exception("Order placement failed")

    order_data = {"symbol": "SYMBOL", "exchange": "NSE", "product": "CNC", "position_size": "5", "action": "BUY", "quantity": "5"}
    with self.assertRaisesRegex(Exception, "Order placement failed"):
        place_smartorder_api(order_data, self.auth_token)

@patch('app.web.broker.broker.dhan.api.order_api.get_positions')
@patch('app.web.broker.broker.dhan.api.order_api.place_order_api')
def test_close_all_positions_api_long_position(self, mock_place_order_api, mock_get_positions):
    mock_get_positions.return_value = ([{'symbol': 'SYMBOL1', 'quantity': 10}], None)
    mock_place_order_api.return_value = (MagicMock(status_code=200), {}, "123")

    res, data = close_all_positions_api(self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(data['message'], "All positions closed successfully.")
    mock_get_positions.assert_called_once()
    mock_place_order_api.assert_called_once()
    self.assertEqual(mock_place_order_api.call_args[0][0]["quantity"], 10)
    self.assertEqual(mock_place_order_api.call_args[0][0]["action"], "SELL")

@patch('app.web.broker.broker.dhan.api.order_api.get_positions')
@patch('app.web.broker.broker.dhan.api.order_api.place_order_api')
def test_close_all_positions_api_short_position(self, mock_place_order_api, mock_get_positions):
    mock_get_positions.return_value = ([{'symbol': 'SYMBOL2', 'quantity': -5}], None)
    mock_place_order_api.return_value = (MagicMock(status_code=200), {}, "123")

    res, data = close_all_positions_api(self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(data['message'], "All positions closed successfully.")
    mock_get_positions.assert_called_once()
    mock_place_order_api.assert_called_once()
    self.assertEqual(mock_place_order_api.call_args[0][0]["quantity"], 5)
    self.assertEqual(mock_place_order_api.call_args[0][0]["action"], "BUY")

@patch('app.web.broker.broker.dhan.api.order_api.get_positions')
@patch('app.web.broker.broker.dhan.api.order_api.place_order_api')
def test_close_all_positions_api_no_positions(self, mock_place_order_api, mock_get_positions):
    mock_get_positions.return_value = ([], None)

    res, data = close_all_positions_api(self.auth_token)

    self.assertIsNone(res)
    self.assertEqual(data['message'], "No positions to close.")
    mock_get_positions.assert_called_once()
    mock_place_order_api.assert_not_called()

@patch('app.web.broker.broker.dhan.api.order_api.get_positions')
@patch('app.web.broker.broker.dhan.api.order_api.place_order_api')
def test_close_all_positions_api_get_positions_error(self, mock_place_order_api, mock_get_positions):
    mock_get_positions.return_value = (None, {"error": "Failed to get positions"})

    res, data = close_all_positions_api(self.auth_token)

    self.assertIsNone(res)
    self.assertEqual(data['error'], "Failed to get positions")
    mock_get_positions.assert_called_once()
    mock_place_order_api.assert_not_called()

@patch('app.web.broker.broker.dhan.api.order_api.get_positions')
@patch('app.web.broker.broker.dhan.api.order_api.place_order_api')
def test_close_all_positions_api_place_order_error(self, mock_place_order_api, mock_get_positions):
    mock_get_positions.return_value = ([{'symbol': 'SYMBOL1', 'quantity': 10}], None)
    mock_place_order_api.return_value = (MagicMock(status_code=400), {"error": "Order failed"}, None)

    res, data = close_all_positions_api(self.auth_token)

    self.assertEqual(res.status_code, 400)
    self.assertEqual(data['error'], "Order failed")
    mock_get_positions.assert_called_once()
    mock_place_order_api.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_token')
@patch('app.web.broker.broker.dhan.api.order_api.transform_data')
@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_place_order_api_order_id_not_found(self, mock_get_httpx_client, mock_transform_data, mock_get_token):
    mock_get_token.return_value = "12345"
    mock_transform_data.return_value = {"tradingSymbol": "SYMBOL", "exchangeSegment": "NSE_EQ", "orderType": "MARKET"}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"status": "success", "message": "Order placed but no ID"})
    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    order_data = {"symbol": "SYMBOL", "exchange": "NSE", "action": "BUY", "quantity": "1"}
    res, response_data, order_id = place_order_api(order_data, self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(response_data['status'], "success")
    self.assertIsNone(order_id)

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_cancel_order_api_success(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"status": "Ok"})
    mock_client = MagicMock()
    mock_client.delete.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    order_id = "12345"
    res, response_data = cancel_order_api(order_id, self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(response_data['status'], "Ok")
    mock_client.delete.assert_called_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_cancel_order_api_failure(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = json.dumps({"status": "Failed", "message": "Order not found"})
    mock_client = MagicMock()
    mock_client.delete.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    order_id = "12345"
    res, response_data = cancel_order_api(order_id, self.auth_token)

    self.assertEqual(res.status_code, 400)
    self.assertEqual(response_data['status'], "Failed")
    mock_client.delete.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_cancel_order_api_exception(self, mock_get_httpx_client):
    mock_client = MagicMock()
    mock_client.delete.side_effect = Exception("Network error")
    mock_get_httpx_client.return_value = mock_client

    order_id = "12345"
    with self.assertRaisesRegex(Exception, "Network error"):
        cancel_order_api(order_id, self.auth_token)

@patch('app.web.broker.broker.dhan.api.order_api.get_token')
@patch('app.web.broker.broker.dhan.api.order_api.transform_data')
@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_modify_order_api_success(self, mock_get_httpx_client, mock_transform_data, mock_get_token):
    mock_get_token.return_value = "12345"
    mock_transform_data.return_value = {"tradingSymbol": "SYMBOL", "exchangeSegment": "NSE_EQ", "orderType": "MARKET"}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"orderId": "123456789"})
    mock_client = MagicMock()
    mock_client.put.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    order_id = "old_order_id"
    new_order_data = {"symbol": "SYMBOL", "exchange": "NSE", "action": "BUY", "quantity": "2"}
    res, response_data, new_order_id = modify_order_api(order_id, new_order_data, self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(response_data['orderId'], "123456789")
    self.assertEqual(new_order_id, "123456789")
    mock_get_token.assert_called_once_with("SYMBOL", "NSE")
    mock_transform_data.assert_called_once()
    mock_client.put.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_token')
@patch('app.web.broker.broker.dhan.api.order_api.transform_data')
@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_modify_order_api_failure(self, mock_get_httpx_client, mock_transform_data, mock_get_token):
    mock_get_token.return_value = "12345"
    mock_transform_data.return_value = {"tradingSymbol": "SYMBOL", "exchangeSegment": "NSE_EQ", "orderType": "MARKET"}

    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = json.dumps({"status": "Failed", "message": "Order modification failed"})
    mock_client = MagicMock()
    mock_client.put.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    order_id = "old_order_id"
    new_order_data = {"symbol": "SYMBOL", "exchange": "NSE", "action": "BUY", "quantity": "2"}
    res, response_data, new_order_id = modify_order_api(order_id, new_order_data, self.auth_token)

    self.assertEqual(res.status_code, 400)
    self.assertEqual(response_data['status'], "Failed")
    self.assertIsNone(new_order_id)
    mock_get_token.assert_called_once_with("SYMBOL", "NSE")
    mock_transform_data.assert_called_once()
    mock_client.put.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_token')
@patch('app.web.broker.broker.dhan.api.order_api.transform_data')
@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_modify_order_api_exception(self, mock_get_httpx_client, mock_transform_data, mock_get_token):
    mock_get_token.return_value = "12345"
    mock_transform_data.return_value = {"tradingSymbol": "SYMBOL", "exchangeSegment": "NSE_EQ", "orderType": "MARKET"}

    mock_client = MagicMock()
    mock_client.put.side_effect = Exception("Network error during modification")
    mock_get_httpx_client.return_value = mock_client

    order_id = "old_order_id"
    new_order_data = {"symbol": "SYMBOL", "exchange": "NSE", "action": "BUY", "quantity": "2"}
    with self.assertRaisesRegex(Exception, "Network error during modification"):
        modify_order_api(order_id, new_order_data, self.auth_token)
    mock_get_token.assert_called_once_with("SYMBOL", "NSE")
    mock_transform_data.assert_called_once()
    mock_client.put.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_cancel_all_orders_api_success(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"status": "Ok"})
    mock_client = MagicMock()
    mock_client.delete.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    res, response_data = cancel_all_orders_api(self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(response_data['status'], "Ok")
    mock_client.delete.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_cancel_all_orders_api_failure(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = json.dumps({"status": "Failed", "message": "No orders to cancel"})
    mock_client = MagicMock()
    mock_client.delete.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    res, response_data = cancel_all_orders_api(self.auth_token)

    self.assertEqual(res.status_code, 400)
    self.assertEqual(response_data['status'], "Failed")
    mock_client.delete.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_cancel_all_orders_api_exception(self, mock_get_httpx_client):
    mock_client = MagicMock()
    mock_client.delete.side_effect = Exception("Network error during bulk cancellation")
    mock_get_httpx_client.return_value = mock_client

    with self.assertRaisesRegex(Exception, "Network error during bulk cancellation"):
        cancel_all_orders_api(self.auth_token)

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_order_book_api_success(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps([
        {"orderId": "1", "symbol": "SYMBOL1", "quantity": 10, "status": "OPEN"},
        {"orderId": "2", "symbol": "SYMBOL2", "quantity": 5, "status": "TRADED"}
    ])
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    res, data = get_order_book_api(self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(len(data), 2)
    self.assertEqual(data[0]['orderId'], "1")
    self.assertEqual(data[1]['symbol'], "SYMBOL2")
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_order_book_api_empty(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps([])
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    res, data = get_order_book_api(self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(len(data), 0)
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_order_book_api_failure(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = json.dumps({"status": "Failed", "message": "Error fetching order book"})
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    res, data = get_order_book_api(self.auth_token)

    self.assertEqual(res.status_code, 400)
    self.assertEqual(data['status'], "Failed")
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_order_book_api_exception(self, mock_get_httpx_client):
    mock_client = MagicMock()
    mock_client.get.side_effect = Exception("Network error during order book fetch")
    mock_get_httpx_client.return_value = mock_client

    with self.assertRaisesRegex(Exception, "Network error during order book fetch"):
        get_order_book_api(self.auth_token)

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_trade_book_api_success(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps([
        {"tradeId": "T1", "symbol": "SYMBOL1", "quantity": 10, "price": 100.0},
        {"tradeId": "T2", "symbol": "SYMBOL2", "quantity": 5, "price": 200.0}
    ])
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    res, data = get_trade_book_api(self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(len(data), 2)
    self.assertEqual(data[0]['tradeId'], "T1")
    self.assertEqual(data[1]['symbol'], "SYMBOL2")
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_trade_book_api_empty(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps([])
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    res, data = get_trade_book_api(self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(len(data), 0)
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_trade_book_api_failure(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = json.dumps({"status": "Failed", "message": "Error fetching trade book"})
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    res, data = get_trade_book_api(self.auth_token)

    self.assertEqual(res.status_code, 400)
    self.assertEqual(data['status'], "Failed")
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_trade_book_api_exception(self, mock_get_httpx_client):
    mock_client = MagicMock()
    mock_client.get.side_effect = Exception("Network error during trade book fetch")
    mock_get_httpx_client.return_value = mock_client

    with self.assertRaisesRegex(Exception, "Network error during trade book fetch"):
        get_trade_book_api(self.auth_token)

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_positions_api_success(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps([
        {"symbol": "SYMBOL1", "quantity": 10, "avgPrice": 100.0},
        {"symbol": "SYMBOL2", "quantity": -5, "avgPrice": 200.0}
    ])
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    res, data = get_positions_api(self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(len(data), 2)
    self.assertEqual(data[0]['symbol'], "SYMBOL1")
    self.assertEqual(data[1]['quantity'], -5)
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_positions_api_empty(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps([])
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    res, data = get_positions_api(self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(len(data), 0)
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_positions_api_failure(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = json.dumps({"status": "Failed", "message": "Error fetching positions"})
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    res, data = get_positions_api(self.auth_token)

    self.assertEqual(res.status_code, 400)
    self.assertEqual(data['status'], "Failed")
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_positions_api_exception(self, mock_get_httpx_client):
    mock_client = MagicMock()
    mock_client.get.side_effect = Exception("Network error during positions fetch")
    mock_get_httpx_client.return_value = mock_client

    with self.assertRaisesRegex(Exception, "Network error during positions fetch"):
        get_positions_api(self.auth_token)

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_holdings_api_success(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps([
        {"holdingId": "H1", "symbol": "SYMBOL1", "quantity": 10, "avgPrice": 100.0},
        {"holdingId": "H2", "symbol": "SYMBOL2", "quantity": 5, "avgPrice": 200.0}
    ])
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    res, data = get_holdings_api(self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(len(data), 2)
    self.assertEqual(data[0]['holdingId'], "H1")
    self.assertEqual(data[1]['symbol'], "SYMBOL2")
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_holdings_api_empty(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps([])
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    res, data = get_holdings_api(self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(len(data), 0)
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_holdings_api_failure(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = json.dumps({"status": "Failed", "message": "Error fetching holdings"})
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    res, data = get_holdings_api(self.auth_token)

    self.assertEqual(res.status_code, 400)
    self.assertEqual(data['status'], "Failed")
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_holdings_api_exception(self, mock_get_httpx_client):
    mock_client = MagicMock()
    mock_client.get.side_effect = Exception("Network error during holdings fetch")
    mock_get_httpx_client.return_value = mock_client

    with self.assertRaisesRegex(Exception, "Network error during holdings fetch"):
        get_holdings_api(self.auth_token)

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_order_details_api_success(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"orderId": "123", "symbol": "SYMBOL1", "quantity": 10, "status": "OPEN"})
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    order_id = "123"
    res, data = get_order_details_api(order_id, self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(data['orderId'], "123")
    self.assertEqual(data['symbol'], "SYMBOL1")
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_order_details_api_empty(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({})
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    order_id = "123"
    res, data = get_order_details_api(order_id, self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(len(data), 0)
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_order_details_api_failure(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = json.dumps({"status": "Failed", "message": "Order not found"})
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    order_id = "123"
    res, data = get_order_details_api(order_id, self.auth_token)

    self.assertEqual(res.status_code, 400)
    self.assertEqual(data['status'], "Failed")
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_order_details_api_exception(self, mock_get_httpx_client):
    mock_client = MagicMock()
    mock_client.get.side_effect = Exception("Network error during order details fetch")
    mock_get_httpx_client.return_value = mock_client

    order_id = "123"
    with self.assertRaisesRegex(Exception, "Network error during order details fetch"):
        get_order_details_api(order_id, self.auth_token)

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_order_details_api_success(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"orderId": "123", "symbol": "SYMBOL1", "quantity": 10, "status": "OPEN"})
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    order_id = "123"
    res, data = get_order_details_api(order_id, self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(data['orderId'], "123")
    self.assertEqual(data['symbol'], "SYMBOL1")
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_order_details_api_empty(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({})
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    order_id = "123"
    res, data = get_order_details_api(order_id, self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(len(data), 0)
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_order_details_api_failure(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = json.dumps({"status": "Failed", "message": "Order not found"})
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    order_id = "123"
    res, data = get_order_details_api(order_id, self.auth_token)

    self.assertEqual(res.status_code, 400)
    self.assertEqual(data['status'], "Failed")
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_order_details_api_exception(self, mock_get_httpx_client):
    mock_client = MagicMock()
    mock_client.get.side_effect = Exception("Network error during order details fetch")
    mock_get_httpx_client.return_value = mock_client

    order_id = "123"
    with self.assertRaisesRegex(Exception, "Network error during order details fetch"):
        get_order_details_api(order_id, self.auth_token)
@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_holdings_api_success(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps([
        {"holdingId": "H1", "symbol": "SYMBOL1", "quantity": 10, "avgPrice": 100.0},
        {"holdingId": "H2", "symbol": "SYMBOL2", "quantity": 5, "avgPrice": 200.0}
    ])
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    res, data = get_holdings_api(self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(len(data), 2)
    self.assertEqual(data[0]['holdingId'], "H1")
    self.assertEqual(data[1]['symbol'], "SYMBOL2")
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_holdings_api_empty(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps([])
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    res, data = get_holdings_api(self.auth_token)

    self.assertEqual(res.status_code, 200)
    self.assertEqual(len(data), 0)
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_holdings_api_failure(self, mock_get_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = json.dumps({"status": "Failed", "message": "Error fetching holdings"})
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_get_httpx_client.return_value = mock_client

    res, data = get_holdings_api(self.auth_token)

    self.assertEqual(res.status_code, 400)
    self.assertEqual(data['status'], "Failed")
    mock_client.get.assert_called_once()

@patch('app.web.broker.broker.dhan.api.order_api.get_httpx_client')
def test_get_holdings_api_exception(self, mock_get_httpx_client):
    mock_client = MagicMock()
    mock_client.get.side_effect = Exception("Network error during holdings fetch")
    mock_get_httpx_client.return_value = mock_client

    with self.assertRaisesRegex(Exception, "Network error during holdings fetch"):
        get_holdings_api(self.auth_token)