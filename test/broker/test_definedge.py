import pytest
pytest.skip("Skipped by user request", allow_module_level=True)
from unittest.mock import patch, MagicMock, PropertyMock
import json
import pandas as pd

from app.web.brokers.definedge.api.auth_api import authenticate_broker
from app.web.brokers.definedge.api.data import BrokerData
from app.web.brokers.definedge.api.order_api import (
    get_open_position, place_order_api, place_smartorder_api,
    cancel_order, modify_order, cancel_all_orders_api
)
from app.core.config import settings

class TestDefinedgeIntegration:
    def setUp(self):
        self.auth_token = "dummy_auth_token"
        self.feed_token = "dummy_feed_token"
        self.user_id = "dummy_user_id"
        self.broker_data = BrokerData(self.auth_token, self.feed_token, self.user_id)

        # Mock settings for API keys
        patcher_api_key = patch('app.core.config.settings.BROKER_API_KEY', "test_api_key")
        patcher_api_secret = patch('app.core.config.settings.BROKER_API_SECRET', "test_api_secret")
        patcher_api_key_market = patch('app.core.config.settings.BROKER_API_KEY_MARKET', "test_api_key_market")
        patcher_api_secret_market = patch('app.core.config.settings.BROKER_API_SECRET_MARKET', "test_api_secret_market")

        self.mock_api_key = patcher_api_key.start()
        self.mock_api_secret = patcher_api_secret.start()
        self.mock_api_key_market = patcher_api_key_market.start()
        self.mock_api_secret_market = patcher_api_secret_market.start()

        self.addCleanup(patcher_api_key.stop)
        self.addCleanup(patcher_api_secret.stop)
        self.addCleanup(patcher_api_key_market.stop)
        self.addCleanup(patcher_api_secret_market.stop)

@patch('app.web.broker.broker.definedge.api.auth_api.login_step2')
def test_authenticate_broker_success(self, mock_login_step2):
    mock_login_step2.return_value = {
    "stat": "Ok",
    "api_session_key": "test_session_key",
    "susertoken": "test_feed_token",
    "uid": "test_user_id"
    }
    auth_string, feed_token, user_id, error = authenticate_broker("dummy_otp_token", "123456")
    self.assertEqual(auth_string, "test_session_key:::test_feed_token:::test_api_key")
    self.assertEqual(feed_token, "test_feed_token")
    self.assertEqual(user_id, "test_user_id")
    self.assertIsNone(error)
    mock_login_step2.assert_called_once_with("dummy_otp_token", "123456", settings.BROKER_API_SECRET)

@patch('app.web.broker.broker.definedge.api.auth_api.login_step2')
def test_authenticate_broker_failed_otp_verification(self, mock_login_step2):
    mock_login_step2.return_value = None
    auth_string, feed_token, user_id, error = authenticate_broker("dummy_otp_token", "123456")
    self.assertIsNone(auth_string)
    self.assertIsNone(feed_token)
    self.assertIsNone(user_id)
    self.assertEqual(error, "Failed to verify OTP")
    mock_login_step2.assert_called_once()

@patch('app.web.broker.broker.definedge.api.auth_api.login_step2')
def test_authenticate_broker_failed_session_key(self, mock_login_step2):
    mock_login_step2.return_value = {
    "stat": "Ok",
    "susertoken": "test_feed_token",
    "uid": "test_user_id"
    }
    auth_string, feed_token, user_id, error = authenticate_broker("dummy_otp_token", "123456")
    self.assertIsNone(auth_string)
    self.assertIsNone(feed_token)
    self.assertIsNone(user_id)
    self.assertEqual(error, "Failed to get API session key")
    mock_login_step2.assert_called_once()

@patch('app.web.broker.broker.definedge.api.auth_api.login_step2')
def test_authenticate_broker_api_error(self, mock_login_step2):
    mock_login_step2.return_value = {
    "stat": "Not_Ok",
    "emsg": "Invalid OTP"
    }
    auth_string, feed_token, user_id, error = authenticate_broker("dummy_otp_token", "123456")
    self.assertIsNone(auth_string)
    self.assertIsNone(feed_token)
    self.assertIsNone(user_id)
    self.assertEqual(error, "Authentication failed: Invalid OTP")
    mock_login_step2.assert_called_once()

@patch('app.web.broker.broker.definedge.api.auth_api.login_step2')
@patch('app.web.broker.broker.definedge.api.auth_api.logger')
def test_authenticate_broker_exception(self, mock_logger, mock_login_step2):
    mock_login_step2.side_effect = Exception("Test exception")
    auth_string, feed_token, user_id, error = authenticate_broker("dummy_otp_token", "123456")
    self.assertIsNone(auth_string)
    self.assertIsNone(feed_token)
    self.assertIsNone(user_id)
    self.assertEqual(error, "Test exception")
    mock_login_step2.assert_called_once()
    mock_logger.error.assert_called_once_with("Authentication error: Test exception")

@patch('app.db.token_db.get_token')
@patch('app.utils.httpx_client.get_httpx_client')
def test_get_quotes_function_success(self, mock_get_httpx_client, mock_get_token):
    mock_get_token.return_value = "12345"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"status": "SUCCESS", "ltp": 100.50})
    mock_response.json.return_value = {"status": "SUCCESS", "ltp": 100.50}
    mock_get_httpx_client.return_value.get.return_value = mock_response

    auth_string = "session_key:::feed_token:::api_key"
    response = get_quotes("SBIN", "NSE", auth_string)

    self.assertEqual(response, {"status": "SUCCESS", "ltp": 100.50})
    mock_get_token.assert_called_once_with("SBIN", "NSE")
    mock_get_httpx_client.return_value.get.assert_called_once()

@patch('app.db.token_db.get_token')
@patch('app.utils.httpx_client.get_httpx_client')
def test_get_quotes_function_api_error(self, mock_get_httpx_client, mock_get_token):
    mock_get_token.return_value = "12345"
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    mock_get_httpx_client.return_value.get.return_value = mock_response

    auth_string = "session_key:::feed_token:::api_key"
    response = get_quotes("SBIN", "NSE", auth_string)

    self.assertEqual(response, {"status": "error", "message": "API returned status 400"})
    mock_get_token.assert_called_once_with("SBIN", "NSE")
    mock_get_httpx_client.return_value.get.assert_called_once()

@patch('app.db.token_db.get_token')
@patch('app.utils.httpx_client.get_httpx_client')
@patch('app.web.broker.broker.definedge.api.data.logger')
def test_get_quotes_function_exception(self, mock_logger, mock_get_httpx_client, mock_get_token):
    mock_get_token.side_effect = Exception("Token error")
    auth_string = "session_key:::feed_token:::api_key"
    response = get_quotes("SBIN", "NSE", auth_string)

    self.assertEqual(response, {"status": "error", "message": "Token error"})
    mock_logger.error.assert_called_once_with("Error getting quotes: Token error")

# Tests for BrokerData.get_quotes
@patch('app.web.broker.broker.definedge.api.data.get_quotes')
def test_broker_data_get_quotes_success(self, mock_get_quotes):
    mock_get_quotes.return_value = {
        "status": "SUCCESS",
        "best_bid_price1": 100.0,
        "best_ask_price1": 101.0,
        "day_open": 99.0,
        "day_high": 102.0,
        "day_low": 98.0,
        "ltp": 100.5,
        "volume": 1000,
        "last_traded_qty": 500
    }
    broker_data_instance = BrokerData("dummy_auth_token")
    quotes = broker_data_instance.get_quotes("SBIN", "NSE")

    self.assertEqual(quotes['bid'], 100.0)
    self.assertEqual(quotes['ask'], 101.0)
    self.assertEqual(quotes['open'], 99.0)
    self.assertEqual(quotes['high'], 102.0)
    self.assertEqual(quotes['low'], 98.0)
    self.assertEqual(quotes['ltp'], 100.5)
    self.assertEqual(quotes['prev_close'], 99.0)
    self.assertEqual(quotes['volume'], 1000)
    self.assertEqual(quotes['oi'], 0)
    mock_get_quotes.assert_called_once_with("SBIN", "NSE", "dummy_auth_token")

@patch('app.web.broker.broker.definedge.api.data.get_quotes')
def test_broker_data_get_quotes_api_error(self, mock_get_quotes):
    mock_get_quotes.return_value = {"status": "error", "message": "API error"}
    broker_data_instance = BrokerData("dummy_auth_token")
    with self.assertRaisesRegex(Exception, "Error fetching quotes: API error"):
        broker_data_instance.get_quotes("SBIN", "NSE")
    mock_get_quotes.assert_called_once_with("SBIN", "NSE", "dummy_auth_token")

@patch('app.web.broker.broker.definedge.api.data.get_quotes')
def test_broker_data_get_quotes_unexpected_status(self, mock_get_quotes):
    mock_get_quotes.return_value = {"status": "FAILURE", "message": "Something went wrong"}
    broker_data_instance = BrokerData("dummy_auth_token")
    with self.assertRaisesRegex(Exception, "Error fetching quotes: API returned status: FAILURE"):
        broker_data_instance.get_quotes("SBIN", "NSE")
    mock_get_quotes.assert_called_once_with("SBIN", "NSE", "dummy_auth_token")

@patch('app.web.broker.broker.definedge.api.data.get_quotes')
@patch('app.web.broker.broker.definedge.api.data.logger')
def test_broker_data_get_quotes_exception(self, mock_logger, mock_get_quotes):
    mock_get_quotes.side_effect = Exception("Network error")
    broker_data_instance = BrokerData("dummy_auth_token")
    with self.assertRaisesRegex(Exception, "Error fetching quotes: Network error"):
        broker_data_instance.get_quotes("SBIN", "NSE")
    mock_logger.error.assert_called_once_with("Error in get_quotes: Network error")
    mock_get_quotes.assert_called_once_with("SBIN", "NSE", "dummy_auth_token")

@patch('app.db.token_db.get_br_symbol')
@patch('app.db.token_db.get_token')
@patch('app.web.broker.broker.definedge.api.data.get_httpx_client')
@patch('app.web.broker.broker.definedge.api.data.pd.to_datetime')
@patch('app.web.broker.broker.definedge.api.data.pd.DataFrame.empty', new_callable=PropertyMock)
@patch('app.web.broker.broker.definedge.api.data.pd.read_csv')
def test_broker_data_get_history_success(self, mock_read_csv, mock_empty, mock_to_datetime, mock_get_httpx_client, mock_get_token, mock_get_br_symbol):
    mock_get_br_symbol.return_value = "SBIN-EQ"
    mock_get_token.return_value = "12345"

    # Mock pd.to_datetime to return specific datetime objects
    mock_to_datetime.side_effect = [
        pd.Timestamp('2023-01-01'),  # from_date
        pd.Timestamp('2023-01-01'),  # to_date
        pd.Timestamp('2023-01-01 09:15:00'), # from_date (intraday)
        pd.Timestamp('2023-01-01 15:30:00')  # to_date (intraday)
    ]

    # Mock httpx response for historical data
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "010120230915,100,102,99,101,1000,0\n010120230916,101,103,100,102,1200,0"
    mock_get_httpx_client.return_value.get.return_value = mock_response

    # Mock pd.read_csv to return a DataFrame
    mock_df = pd.DataFrame({
        'datetime': ['010120230915', '010120230916'],
        'open': [100, 101],
        'high': [102, 103],
        'low': [99, 100],
        'close': [101, 102],
        'volume': [1000, 1200],
        'oi': [0, 0]
    })
    mock_df['timestamp'] = pd.to_datetime(mock_df['datetime'], format='%d%m%Y%H%M')
    mock_df = mock_df.drop('datetime', axis=1)

    mock_read_csv.return_value = mock_df
    mock_empty.return_value = False

    broker_data_instance = BrokerData("session_key:::feed_token:::api_key")
    df = broker_data_instance.get_history("SBIN", "NSE", "1m", "2023-01-01", "2023-01-01")

    self.assertIsInstance(df, pd.DataFrame)
    self.assertFalse(df.empty)
    self.assertEqual(len(df), 2)
    self.assertIn('timestamp', df.columns)
    self.assertIn('open', df.columns)
    self.assertIn('close', df.columns)
    mock_get_br_symbol.assert_called_once_with("SBIN", "NSE")
    mock_get_token.assert_called_once_with("SBIN", "NSE")
    mock_get_httpx_client.return_value.get.assert_called_once()
    mock_read_csv.assert_called_once()

@patch('app.db.token_db.get_br_symbol')
@patch('app.db.token_db.get_token')
def test_broker_data_get_history_unsupported_timeframe(self, mock_get_token, mock_get_br_symbol):
    mock_get_br_symbol.return_value = "SBIN-EQ"
    mock_get_token.return_value = "12345"

    broker_data_instance = BrokerData("session_key:::feed_token:::api_key")
    df = broker_data_instance.get_history("SBIN", "NSE", "2m", "2023-01-01", "2023-01-01")

    self.assertIsInstance(df, pd.DataFrame)
    self.assertTrue(df.empty)
    self.assertEqual(df.columns.tolist(), ['close', 'high', 'low', 'open', 'timestamp', 'volume', 'oi'])

@patch('app.db.token_db.get_br_symbol')
@patch('app.db.token_db.get_token')
@patch('app.web.broker.broker.definedge.api.data.get_httpx_client')
@patch('app.web.broker.broker.definedge.api.data.pd.to_datetime')
@patch('app.web.broker.broker.definedge.api.data.logger')
def test_broker_data_get_history_api_error_chunk(self, mock_logger, mock_to_datetime, mock_get_httpx_client, mock_get_token, mock_get_br_symbol):
    mock_get_br_symbol.return_value = "SBIN-EQ"
    mock_get_token.return_value = "12345"
    mock_to_datetime.side_effect = [
        pd.Timestamp('2023-01-01'),  # from_date
        pd.Timestamp('2023-01-01'),  # to_date
        pd.Timestamp('2023-01-01 09:15:00'), # from_date (intraday)
        pd.Timestamp('2023-01-01 15:30:00')  # to_date (intraday)
    ]

    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "API Error"
    mock_get_httpx_client.return_value.get.return_value = mock_response

    broker_data_instance = BrokerData("session_key:::feed_token:::api_key")
    df = broker_data_instance.get_history("SBIN", "NSE", "1m", "2023-01-01", "2023-01-01")

    self.assertIsInstance(df, pd.DataFrame)
    self.assertTrue(df.empty)
    mock_logger.warning.assert_called_with("Debug - Definedge API returned status 400")

@patch('app.db.token_db.get_br_symbol')
@patch('app.db.token_db.get_token')
@patch('app.web.broker.broker.definedge.api.data.get_httpx_client')
@patch('app.web.broker.broker.definedge.api.data.pd.to_datetime')
@patch('app.web.broker.broker.definedge.api.data.pd.read_csv')
@patch('app.web.broker.broker.definedge.api.data.pd.DataFrame.resample')
def test_broker_data_get_history_resampling(self, mock_resample, mock_read_csv, mock_to_datetime, mock_get_httpx_client, mock_get_token, mock_get_br_symbol):
    mock_get_br_symbol.return_value = "SBIN-EQ"
    mock_get_token.return_value = "12345"
    mock_to_datetime.side_effect = [
        pd.Timestamp('2023-01-01'),  # from_date
        pd.Timestamp('2023-01-01'),  # to_date
        pd.Timestamp('2023-01-01 09:15:00'), # from_date (intraday)
        pd.Timestamp('2023-01-01 15:30:00')  # to_date (intraday)
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "010120230915,100,102,99,101,1000,0\n010120230916,101,103,100,102,1200,0"
    mock_get_httpx_client.return_value.get.return_value = mock_response

    # Mock pd.read_csv to return a DataFrame
    mock_df = pd.DataFrame({
        'datetime': ['010120230915', '010120230916'],
        'open': [100, 101],
        'high': [102, 103],
        'low': [99, 100],
        'close': [101, 102],
        'volume': [1000, 1200],
        'oi': [0, 0]
    })
    mock_df['timestamp'] = pd.to_datetime(mock_df['datetime'], format='%d%m%Y%H%M')
    mock_df = mock_df.drop('datetime', axis=1)
    mock_read_csv.return_value = mock_df

    # Mock the resample object and its methods
    mock_resampled_group = MagicMock()
    mock_resampled_group.first.return_value = pd.Series([100], name='open')
    mock_resampled_group.max.return_value = pd.Series([102], name='high')
    mock_resampled_group.min.return_value = pd.Series([99], name='low')
    mock_resampled_group.last.return_value = pd.Series([101], name='close')
    mock_resampled_group.sum.return_value = pd.Series([2200], name='volume')
    mock_resampled_group.last.return_value = pd.Series([0], name='oi') # Added for OI
    mock_resample.return_value.return_value = mock_resampled_group # For resample().agg()

    broker_data_instance = BrokerData("session_key:::feed_token:::api_key")
    df = broker_data_instance.get_history("SBIN", "NSE", "5m", "2023-01-01", "2023-01-01")

    self.assertIsInstance(df, pd.DataFrame)
    self.assertFalse(df.empty)
    mock_resample.assert_called_once_with('5min', offset='15min')

    @patch('app.web.broker.broker.definedge.api.data.get_quotes')
    def test_broker_data_get_depth_success(self, mock_get_quotes):
        mock_get_quotes.return_value = {
            "status": "SUCCESS",
            "best_bid_price1": 100.0, "best_bid_qty1": 100,
            "best_bid_price2": 99.9, "best_bid_qty2": 200,
            "best_ask_price1": 100.1, "best_ask_qty1": 150,
            "best_ask_price2": 100.2, "best_ask_qty2": 250,
            "day_high": 102.0, "day_low": 98.0,
            "ltp": 100.0, "last_traded_qty": 50,
            "day_open": 99.0, "volume": 10000
        }
        broker_data_instance = BrokerData("dummy_auth_token")
        depth = broker_data_instance.get_depth("SBIN", "NSE")

        self.assertIsInstance(depth, dict)
        self.assertIn('bids', depth)
        self.assertIn('asks', depth)
        self.assertEqual(len(depth['bids']), 5)
        self.assertEqual(len(depth['asks']), 5)
        self.assertEqual(depth['bids'][0]['price'], 100.0)
        self.assertEqual(depth['bids'][0]['quantity'], 100)
        self.assertEqual(depth['asks'][0]['price'], 100.1)
        self.assertEqual(depth['asks'][0]['quantity'], 150)
        self.assertEqual(depth['high'], 102.0)
        self.assertEqual(depth['low'], 98.0)
        self.assertEqual(depth['ltp'], 100.0)
        self.assertEqual(depth['ltq'], 50)
        self.assertEqual(depth['open'], 99.0)
        self.assertEqual(depth['prev_close'], 99.0)
        self.assertEqual(depth['volume'], 10000)
        self.assertEqual(depth['oi'], 0)
        self.assertEqual(depth['totalbuyqty'], 300) # 100 + 200
        self.assertEqual(depth['totalsellqty'], 400) # 150 + 250
        mock_get_quotes.assert_called_once_with("SBIN", "NSE", "dummy_auth_token")

    @patch('app.web.broker.broker.definedge.api.data.get_quotes')
    def test_broker_data_get_depth_api_error(self, mock_get_quotes):
        mock_get_quotes.return_value = {"status": "error", "message": "API depth error"}
        broker_data_instance = BrokerData("dummy_auth_token")
        with self.assertRaisesRegex(Exception, "Error fetching market depth: API depth error"):
            broker_data_instance.get_depth("SBIN", "NSE")
        mock_get_quotes.assert_called_once_with("SBIN", "NSE", "dummy_auth_token")

    @patch('app.web.broker.broker.definedge.api.data.get_quotes')
    def test_broker_data_get_depth_unexpected_status(self, mock_get_quotes):
        mock_get_quotes.return_value = {"status": "FAILURE", "message": "Depth failed"}
        broker_data_instance = BrokerData("dummy_auth_token")
        with self.assertRaisesRegex(Exception, "Error fetching market depth: API returned status: FAILURE"):
            broker_data_instance.get_depth("SBIN", "NSE")
        mock_get_quotes.assert_called_once_with("SBIN", "NSE", "dummy_auth_token")

    @patch('app.web.broker.broker.definedge.api.data.get_quotes')
    @patch('app.web.broker.broker.definedge.api.data.logger')
    def test_broker_data_get_depth_exception(self, mock_logger, mock_get_quotes):
        mock_get_quotes.side_effect = Exception("Depth network error")
        broker_data_instance = BrokerData("dummy_auth_token")
        with self.assertRaisesRegex(Exception, "Error fetching market depth: Depth network error"):
            broker_data_instance.get_depth("SBIN", "NSE")
        mock_logger.error.assert_called_once_with("Error in get_depth: Depth network error")
        mock_get_quotes.assert_called_once_with("SBIN", "NSE", "dummy_auth_token")

    @patch('app.db.token_db.get_br_symbol')
    @patch('app.web.broker.broker.definedge.api.order_api.get_positions')
    def test_get_open_position_success_found(self, mock_get_positions, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "SBIN-EQ"
        mock_get_positions.return_value = {
            "stat": "Ok",
            "positions": [
                {"tradingsymbol": "SBIN-EQ", "exchange": "NSE", "product": "MIS", "net_quantity": "10"}
            ]
        }
        net_qty = get_open_position("SBIN", "NSE", "MIS", self.auth_token)
        self.assertEqual(net_qty, "10")
        mock_get_br_symbol.assert_called_once_with("SBIN", "NSE")
        mock_get_positions.assert_called_once_with(self.auth_token)

    @patch('app.db.token_db.get_br_symbol')
    @patch('app.web.broker.broker.definedge.api.order_api.get_positions')
    def test_get_open_position_success_not_found(self, mock_get_positions, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "SBIN-EQ"
        mock_get_positions.return_value = {
            "stat": "Ok",
            "positions": [
                {"tradingsymbol": "RELIANCE-EQ", "exchange": "NSE", "product": "MIS", "net_quantity": "10"}
            ]
        }
        net_qty = get_open_position("SBIN", "NSE", "MIS", self.auth_token)
        self.assertEqual(net_qty, "0")
        mock_get_br_symbol.assert_called_once_with("SBIN", "NSE")
        mock_get_positions.assert_called_once_with(self.auth_token)

    @patch('app.db.token_db.get_br_symbol')
    @patch('app.web.broker.broker.definedge.api.order_api.get_positions')
    def test_get_open_position_api_error(self, mock_get_positions, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "SBIN-EQ"
        mock_get_positions.return_value = {"stat": "Not_Ok", "emsg": "API Error"}
        net_qty = get_open_position("SBIN", "NSE", "MIS", self.auth_token)
        self.assertEqual(net_qty, "0")
        mock_get_br_symbol.assert_called_once_with("SBIN", "NSE")
        mock_get_positions.assert_called_once_with(self.auth_token)

    @patch('app.db.token_db.get_br_symbol')
    @patch('app.web.broker.broker.definedge.api.order_api.get_positions')
    def test_get_open_position_empty_response(self, mock_get_positions, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "SBIN-EQ"
        mock_get_positions.return_value = None
        net_qty = get_open_position("SBIN", "NSE", "MIS", self.auth_token)
        self.assertEqual(net_qty, "0")
        mock_get_br_symbol.assert_called_once_with("SBIN", "NSE")
        mock_get_positions.assert_called_once_with(self.auth_token)

    @patch('app.db.token_db.get_br_symbol')
    @patch('app.web.broker.broker.definedge.api.order_api.get_positions')
    def test_get_open_position_list_response(self, mock_get_positions, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "SBIN-EQ"
        mock_get_positions.return_value = [
            {"tradingsymbol": "SBIN-EQ", "exchange": "NSE", "product": "MIS", "net_quantity": "10"}
        ]
        net_qty = get_open_position("SBIN", "NSE", "MIS", self.auth_token)
        self.assertEqual(net_qty, "10")
        mock_get_br_symbol.assert_called_once_with("SBIN", "NSE")
        mock_get_positions.assert_called_once_with(self.auth_token)

    @patch('app.web.broker.broker.definedge.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.definedge.api.order_api.get_token')
    @patch('app.web.broker.broker.definedge.api.order_api.transform_data')
    def test_place_order_api_success(self, mock_transform_data, mock_get_token, mock_get_httpx_client):
        mock_get_token.return_value = "12345"
        mock_transform_data.return_value = {"key": "value"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stat": "Ok", "norenordno": "ORD123"}
        mock_response.text = json.dumps({"stat": "Ok", "norenordno": "ORD123"})
        mock_get_httpx_client.return_value.post.return_value = mock_response

        data = {"symbol": "SBIN", "exchange": "NSE"}
        res, response_data, orderid = place_order_api(data, self.auth_token)

        self.assertEqual(orderid, "ORD123")
        self.assertEqual(response_data, {"stat": "Ok", "norenordno": "ORD123"})
        self.assertEqual(res.status, 200)
        mock_get_token.assert_called_once_with("SBIN", "NSE")
        mock_transform_data.assert_called_once_with(data, "12345")
        mock_get_httpx_client.return_value.post.assert_called_once()

    @patch('app.web.broker.broker.definedge.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.definedge.api.order_api.get_token')
    @patch('app.web.broker.broker.definedge.api.order_api.transform_data')
    def test_place_order_api_api_error(self, mock_transform_data, mock_get_token, mock_get_httpx_client):
        mock_get_token.return_value = "12345"
        mock_transform_data.return_value = {"key": "value"}
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"stat": "Not_Ok", "emsg": "Invalid order"}
        mock_response.text = json.dumps({"stat": "Not_Ok", "emsg": "Invalid order"})
        mock_get_httpx_client.return_value.post.return_value = mock_response

        data = {"symbol": "SBIN", "exchange": "NSE"}
        res, response_data, orderid = place_order_api(data, self.auth_token)

        self.assertIsNone(orderid)
        self.assertEqual(response_data, {"stat": "Not_Ok", "emsg": "Invalid order"})
        self.assertEqual(res.status, 400)

    @patch('app.web.broker.broker.definedge.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.definedge.api.order_api.get_token')
    @patch('app.web.broker.broker.definedge.api.order_api.transform_data')
    def test_place_order_api_json_decode_error(self, mock_transform_data, mock_get_token, mock_get_httpx_client):
        mock_get_token.return_value = "12345"
        mock_transform_data.return_value = {"key": "value"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Invalid JSON response"
        mock_get_httpx_client.return_value.post.return_value = mock_response

        data = {"symbol": "SBIN", "exchange": "NSE"}
        res, response_data, orderid = place_order_api(data, self.auth_token)

        self.assertIsNone(orderid)
        self.assertIn("Invalid JSON response from API", response_data["emsg"])
        self.assertEqual(res.status, 200)

    @patch('app.web.broker.broker.definedge.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.definedge.api.order_api.get_token')
    @patch('app.web.broker.broker.definedge.api.order_api.transform_data')
    def test_place_order_api_http_status_error(self, mock_transform_data, mock_get_token, mock_get_httpx_client):
        mock_get_token.return_value = "12345"
        mock_transform_data.return_value = {"key": "value"}
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_response
        )
        mock_get_httpx_client.return_value.post.return_value = mock_response

        data = {"symbol": "SBIN", "exchange": "NSE"}
        res, response_data, orderid = place_order_api(data, self.auth_token)

        self.assertIsNone(orderid)
        self.assertIn("HTTP 500", response_data["emsg"])
        self.assertEqual(res.status, 500)

    @patch('app.web.broker.broker.definedge.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.definedge.api.order_api.get_token')
    @patch('app.web.broker.broker.definedge.api.order_api.transform_data')
    @patch('app.web.broker.broker.definedge.api.order_api.logger')
    def test_place_order_api_exception(self, mock_logger, mock_transform_data, mock_get_token, mock_get_httpx_client):
        mock_get_token.side_effect = Exception("Token error")
        data = {"symbol": "SBIN", "exchange": "NSE"}
        res, response_data, orderid = place_order_api(data, self.auth_token)

        self.assertIsNone(orderid)
        self.assertEqual(response_data, {"stat": "Not_Ok", "emsg": "Error: Token error"})
        self.assertEqual(res.status, 500)
        mock_logger.error.assert_called()

    @patch('app.web.broker.broker.definedge.api.order_api.get_open_position')
    @patch('app.web.broker.broker.definedge.api.order_api.place_order_api')
    @patch('app.web.broker.broker.definedge.api.order_api.map_product_type')
    def test_place_smartorder_api_no_action_zero_position(self, mock_map_product_type, mock_place_order_api, mock_get_open_position):
        mock_get_open_position.return_value = "0"
        mock_map_product_type.return_value = "MIS"
        data = {"symbol": "SBIN", "exchange": "NSE", "product": "MIS", "position_size": "0"}
        res, response_data, orderid = place_smartorder_api(data, self.auth_token)
        self.assertIsNone(res)
        self.assertEqual(response_data, {"status": "success", "message": "No position to square off"})
        self.assertIsNone(orderid)
        mock_get_open_position.assert_called_once_with("SBIN", "NSE", "MIS", self.auth_token)
        mock_place_order_api.assert_not_called()

    @patch('app.web.broker.broker.definedge.api.order_api.get_open_position')
    @patch('app.web.broker.broker.definedge.api.order_api.place_order_api')
    @patch('app.web.broker.broker.definedge.api.order_api.map_product_type')
    def test_place_smartorder_api_no_action_matching_position(self, mock_map_product_type, mock_place_order_api, mock_get_open_position):
        mock_get_open_position.return_value = "10"
        mock_map_product_type.return_value = "MIS"
        data = {"symbol": "SBIN", "exchange": "NSE", "product": "MIS", "position_size": "10"}
        res, response_data, orderid = place_smartorder_api(data, self.auth_token)
        self.assertIsNone(res)
        self.assertEqual(response_data, {"status": "success", "message": "Position already at target size"})
        self.assertIsNone(orderid)
        mock_get_open_position.assert_called_once_with("SBIN", "NSE", "MIS", self.auth_token)
        mock_place_order_api.assert_not_called()

    @patch('app.web.broker.broker.definedge.api.order_api.get_open_position')
    @patch('app.web.broker.broker.definedge.api.order_api.place_order_api')
    @patch('app.web.broker.broker.definedge.api.order_api.map_product_type')
    def test_place_smartorder_api_square_off_long_position(self, mock_map_product_type, mock_place_order_api, mock_get_open_position):
        mock_get_open_position.return_value = "10"
        mock_map_product_type.return_value = "MIS"
        mock_place_order_api.return_value = (MagicMock(status=200), {"stat": "Ok", "norenordno": "ORD123"}, "ORD123")
        data = {"symbol": "SBIN", "exchange": "NSE", "product": "MIS", "position_size": "0"}
        res, response_data, orderid = place_smartorder_api(data, self.auth_token)
        self.assertEqual(orderid, "ORD123")
        self.assertEqual(response_data, {"stat": "Ok", "norenordno": "ORD123"})
        self.assertEqual(res.status, 200)
        mock_get_open_position.assert_called_once_with("SBIN", "NSE", "MIS", self.auth_token)
        mock_place_order_api.assert_called_once()
        self.assertEqual(mock_place_order_api.call_args[0][0]["action"], "SELL")
        self.assertEqual(mock_place_order_api.call_args[0][0]["quantity"], "10")

    @patch('app.web.broker.broker.definedge.api.order_api.get_open_position')
    @patch('app.web.broker.broker.definedge.api.order_api.place_order_api')
    @patch('app.web.broker.broker.definedge.api.order_api.map_product_type')
    def test_place_smartorder_api_square_off_short_position(self, mock_map_product_type, mock_place_order_api, mock_get_open_position):
        mock_get_open_position.return_value = "-10"
        mock_map_product_type.return_value = "MIS"
        mock_place_order_api.return_value = (MagicMock(status=200), {"stat": "Ok", "norenordno": "ORD123"}, "ORD123")
        data = {"symbol": "SBIN", "exchange": "NSE", "product": "MIS", "position_size": "0"}
        res, response_data, orderid = place_smartorder_api(data, self.auth_token)
        self.assertEqual(orderid, "ORD123")
        self.assertEqual(response_data, {"stat": "Ok", "norenordno": "ORD123"})
        self.assertEqual(res.status, 200)
        mock_get_open_position.assert_called_once_with("SBIN", "NSE", "MIS", self.auth_token)
        mock_place_order_api.assert_called_once()
        self.assertEqual(mock_place_order_api.call_args[0][0]["action"], "BUY")
        self.assertEqual(mock_place_order_api.call_args[0][0]["quantity"], "10")

    @patch('app.web.broker.broker.definedge.api.order_api.get_open_position')
    @patch('app.web.broker.broker.definedge.api.order_api.place_order_api')
    @patch('app.web.broker.broker.definedge.api.order_api.map_product_type')
    def test_place_smartorder_api_open_new_long_position(self, mock_map_product_type, mock_place_order_api, mock_get_open_position):
        mock_get_open_position.return_value = "0"
        mock_map_product_type.return_value = "MIS"
        mock_place_order_api.return_value = (MagicMock(status=200), {"stat": "Ok", "norenordno": "ORD123"}, "ORD123")
        data = {"symbol": "SBIN", "exchange": "NSE", "product": "MIS", "position_size": "10"}
        res, response_data, orderid = place_smartorder_api(data, self.auth_token)
        self.assertEqual(orderid, "ORD123")
        self.assertEqual(response_data, {"stat": "Ok", "norenordno": "ORD123"})
        self.assertEqual(res.status, 200)
        mock_get_open_position.assert_called_once_with("SBIN", "NSE", "MIS", self.auth_token)
        mock_place_order_api.assert_called_once()
        self.assertEqual(mock_place_order_api.call_args[0][0]["action"], "BUY")
        self.assertEqual(mock_place_order_api.call_args[0][0]["quantity"], "10")

    @patch('app.web.broker.broker.definedge.api.order_api.get_open_position')
    @patch('app.web.broker.broker.definedge.api.order_api.place_order_api')
    @patch('app.web.broker.broker.definedge.api.order_api.map_product_type')
    def test_place_smartorder_api_open_new_short_position(self, mock_map_product_type, mock_place_order_api, mock_get_open_position):
        mock_get_open_position.return_value = "0"
        mock_map_product_type.return_value = "MIS"
        mock_place_order_api.return_value = (MagicMock(status=200), {"stat": "Ok", "norenordno": "ORD123"}, "ORD123")
        data = {"symbol": "SBIN", "exchange": "NSE", "product": "MIS", "position_size": "-10"}
        res, response_data, orderid = place_smartorder_api(data, self.auth_token)
        self.assertEqual(orderid, "ORD123")
        self.assertEqual(response_data, {"stat": "Ok", "norenordno": "ORD123"})
        self.assertEqual(res.status, 200)
        mock_get_open_position.assert_called_once_with("SBIN", "NSE", "MIS", self.auth_token)
        mock_place_order_api.assert_called_once()
        self.assertEqual(mock_place_order_api.call_args[0][0]["action"], "SELL")
        self.assertEqual(mock_place_order_api.call_args[0][0]["quantity"], "10")

    @patch('app.web.broker.broker.definedge.api.order_api.get_open_position')
    @patch('app.web.broker.broker.definedge.api.order_api.place_order_api')
    @patch('app.web.broker.broker.definedge.api.order_api.map_product_type')
    def test_place_smartorder_api_increase_long_position(self, mock_map_product_type, mock_place_order_api, mock_get_open_position):
        mock_get_open_position.return_value = "5"
        mock_map_product_type.return_value = "MIS"
        mock_place_order_api.return_value = (MagicMock(status=200), {"stat": "Ok", "norenordno": "ORD123"}, "ORD123")
        data = {"symbol": "SBIN", "exchange": "NSE", "product": "MIS", "position_size": "15"}
        res, response_data, orderid = place_smartorder_api(data, self.auth_token)
        self.assertEqual(orderid, "ORD123")
        self.assertEqual(response_data, {"stat": "Ok", "norenordno": "ORD123"})
        self.assertEqual(res.status, 200)
        mock_get_open_position.assert_called_once_with("SBIN", "NSE", "MIS", self.auth_token)
        mock_place_order_api.assert_called_once()
        self.assertEqual(mock_place_order_api.call_args[0][0]["action"], "BUY")
        self.assertEqual(mock_place_order_api.call_args[0][0]["quantity"], "10")

    @patch('app.web.broker.broker.definedge.api.order_api.get_open_position')
    @patch('app.web.broker.broker.definedge.api.order_api.place_order_api')
    @patch('app.web.broker.broker.definedge.api.order_api.map_product_type')
    def test_place_smartorder_api_decrease_long_position(self, mock_map_product_type, mock_place_order_api, mock_get_open_position):
        mock_get_open_position.return_value = "15"
        mock_map_product_type.return_value = "MIS"
        mock_place_order_api.return_value = (MagicMock(status=200), {"stat": "Ok", "norenordno": "ORD123"}, "ORD123")
        data = {"symbol": "SBIN", "exchange": "NSE", "product": "MIS", "position_size": "5"}
        res, response_data, orderid = place_smartorder_api(data, self.auth_token)
        self.assertEqual(orderid, "ORD123")
        self.assertEqual(response_data, {"stat": "Ok", "norenordno": "ORD123"})
        self.assertEqual(res.status, 200)
        mock_get_open_position.assert_called_once_with("SBIN", "NSE", "MIS", self.auth_token)
        mock_place_order_api.assert_called_once()
        self.assertEqual(mock_place_order_api.call_args[0][0]["action"], "SELL")
        self.assertEqual(mock_place_order_api.call_args[0][0]["quantity"], "10")

    @patch('app.web.broker.broker.definedge.api.order_api.get_open_position')
    @patch('app.web.broker.broker.definedge.api.order_api.place_order_api')
    @patch('app.web.broker.broker.definedge.api.order_api.map_product_type')
    def test_place_smartorder_api_increase_short_position(self, mock_map_product_type, mock_place_order_api, mock_get_open_position):
        mock_get_open_position.return_value = "-5"
        mock_map_product_type.return_value = "MIS"
        mock_place_order_api.return_value = (MagicMock(status=200), {"stat": "Ok", "norenordno": "ORD123"}, "ORD123")
        data = {"symbol": "SBIN", "exchange": "NSE", "product": "MIS", "position_size": "-15"}
        res, response_data, orderid = place_smartorder_api(data, self.auth_token)
        self.assertEqual(orderid, "ORD123")
        self.assertEqual(response_data, {"stat": "Ok", "norenordno": "ORD123"})
        self.assertEqual(res.status, 200)
        mock_get_open_position.assert_called_once_with("SBIN", "NSE", "MIS", self.auth_token)
        mock_place_order_api.assert_called_once()
        self.assertEqual(mock_place_order_api.call_args[0][0]["action"], "SELL")
        self.assertEqual(mock_place_order_api.call_args[0][0]["quantity"], "10")

    @patch('app.web.broker.broker.definedge.api.order_api.get_open_position')
    @patch('app.web.broker.broker.definedge.api.order_api.place_order_api')
    @patch('app.web.broker.broker.definedge.api.order_api.map_product_type')
    def test_place_smartorder_api_decrease_short_position(self, mock_map_product_type, mock_place_order_api, mock_get_open_position):
        mock_get_open_position.return_value = "-15"
        mock_map_product_type.return_value = "MIS"
        mock_place_order_api.return_value = (MagicMock(status=200), {"stat": "Ok", "norenordno": "ORD123"}, "ORD123")
        data = {"symbol": "SBIN", "exchange": "NSE", "product": "MIS", "position_size": "-5"}
        res, response_data, orderid = place_smartorder_api(data, self.auth_token)
        self.assertEqual(orderid, "ORD123")
        self.assertEqual(response_data, {"stat": "Ok", "norenordno": "ORD123"})
        self.assertEqual(res.status, 200)
        mock_get_open_position.assert_called_once_with("SBIN", "NSE", "MIS", self.auth_token)
        mock_place_order_api.assert_called_once()
        self.assertEqual(mock_place_order_api.call_args[0][0]["action"], "BUY")
        self.assertEqual(mock_place_order_api.call_args[0][0]["quantity"], "10")

    def test_place_smartorder_api_missing_parameters(self):
        data = {"exchange": "NSE", "product": "MIS", "position_size": "10"}  # Missing symbol
        res, response_data, orderid = place_smartorder_api(data, self.auth_token)
        self.assertIsNone(res)
        self.assertEqual(response_data, {"status": "error", "message": "No action required or invalid parameters"})
        self.assertIsNone(orderid)

    @patch('app.web.broker.broker.definedge.api.order_api.get_open_position', side_effect=Exception("Test Exception"))
    @patch('app.web.broker.broker.definedge.api.order_api.logger')
    def test_place_smartorder_api_exception(self, mock_logger, mock_get_open_position):
        data = {"symbol": "SBIN", "exchange": "NSE", "product": "MIS", "position_size": "10"}
        res, response_data, orderid = place_smartorder_api(data, self.auth_token)
        self.assertIsNone(res)
        self.assertIn("Error in place_smartorder_api: Test Exception", response_data["message"])
        self.assertIsNone(orderid)
        mock_logger.error.assert_called_once()

    @patch('app.db.token_db.get_br_symbol')
    @patch('app.web.broker.broker.definedge.api.order_api.get_positions')
    def test_get_open_position_product_type_field(self, mock_get_positions, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "SBIN-EQ"
        mock_get_positions.return_value = {
            "stat": "Ok",
            "positions": [
                {"tradingsymbol": "SBIN-EQ", "exchange": "NSE", "product_type": "MIS", "net_quantity": "10"}
            ]
        }
        net_qty = get_open_position("SBIN", "NSE", "MIS", self.auth_token)
        self.assertEqual(net_qty, "10")
        mock_get_br_symbol.assert_called_once_with("SBIN", "NSE")
        mock_get_positions.assert_called_once_with(self.auth_token)

    @patch('app.db.token_db.get_br_symbol')
    @patch('app.web.broker.broker.definedge.api.order_api.get_positions')
    def test_get_open_position_net_qty_different_field(self, mock_get_positions, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "SBIN-EQ"
        mock_get_positions.return_value = {
            "stat": "Ok",
            "positions": [
                {"tradingsymbol": "SBIN-EQ", "exchange": "NSE", "product": "MIS", "netqty": "15"}
            ]
        }
        net_qty = get_open_position("SBIN", "NSE", "MIS", self.auth_token)
        self.assertEqual(net_qty, "15")
        mock_get_br_symbol.assert_called_once_with("SBIN", "NSE")
        mock_get_positions.assert_called_once_with(self.auth_token)

    @patch('app.web.broker.broker.definedge.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.definedge.api.order_api.get_token')
    @patch('app.web.broker.broker.definedge.api.order_api.transform_data')
    def test_cancel_order_success(self, mock_transform_data, mock_get_token, mock_get_httpx_client):
        mock_get_token.return_value = "12345"
        mock_transform_data.return_value = {"key": "value"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stat": "Ok", "norenordno": "ORD123"}
        mock_response.text = json.dumps({"stat": "Ok", "norenordno": "ORD123"})
        mock_get_httpx_client.return_value.post.return_value = mock_response

        data = {"orderid": "ORD123", "exchange": "NSE"}
        res, response_data, orderid = cancel_order(data, self.auth_token)

        self.assertEqual(orderid, "ORD123")
        self.assertEqual(response_data, {"stat": "Ok", "norenordno": "ORD123"})
        self.assertEqual(res.status, 200)
        mock_get_token.assert_called_once_with(None, "NSE") # Symbol can be None for cancel order
        mock_transform_data.assert_called_once_with(data, "12345")
        mock_get_httpx_client.return_value.post.assert_called_once()

    @patch('app.web.broker.broker.definedge.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.definedge.api.order_api.get_token')
    @patch('app.web.broker.broker.definedge.api.order_api.transform_data')
    def test_cancel_order_api_error(self, mock_transform_data, mock_get_token, mock_get_httpx_client):
        mock_get_token.return_value = "12345"
        mock_transform_data.return_value = {"key": "value"}
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"stat": "Not_Ok", "emsg": "Invalid order id"}
        mock_response.text = json.dumps({"stat": "Not_Ok", "emsg": "Invalid order id"})
        mock_get_httpx_client.return_value.post.return_value = mock_response

        data = {"orderid": "ORD123", "exchange": "NSE"}
        res, response_data, orderid = cancel_order(data, self.auth_token)

        self.assertIsNone(orderid)
        self.assertEqual(response_data, {"stat": "Not_Ok", "emsg": "Invalid order id"})
        self.assertEqual(res.status, 400)

    @patch('app.web.broker.broker.definedge.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.definedge.api.order_api.get_token')
    @patch('app.web.broker.broker.definedge.api.order_api.transform_data')
    @patch('app.web.broker.broker.definedge.api.order_api.logger')
    def test_cancel_order_exception(self, mock_logger, mock_transform_data, mock_get_token, mock_get_httpx_client):
        mock_get_token.side_effect = Exception("Token error")
        data = {"orderid": "ORD123", "exchange": "NSE"}
        res, response_data, orderid = cancel_order(data, self.auth_token)

        self.assertIsNone(orderid)
        self.assertEqual(response_data, {"stat": "Not_Ok", "emsg": "Error: Token error"})
        self.assertEqual(res.status, 500)
        mock_logger.error.assert_called_once()

    @patch('app.web.broker.broker.definedge.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.definedge.api.order_api.get_token')
    @patch('app.web.broker.broker.definedge.api.order_api.transform_data')
    def test_modify_order_success(self, mock_transform_data, mock_get_token, mock_get_httpx_client):
        mock_get_token.return_value = "12345"
        mock_transform_data.return_value = {"key": "value"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stat": "Ok", "norenordno": "ORD123"}
        mock_response.text = json.dumps({"stat": "Ok", "norenordno": "ORD123"})
        mock_get_httpx_client.return_value.post.return_value = mock_response

        data = {"orderid": "ORD123", "exchange": "NSE", "new_quantity": "10"}
        res, response_data, orderid = modify_order(data, self.auth_token)

        self.assertEqual(orderid, "ORD123")
        self.assertEqual(response_data, {"stat": "Ok", "norenordno": "ORD123"})
        self.assertEqual(res.status, 200)
        mock_get_token.assert_called_once_with(None, "NSE") # Symbol can be None for modify order
        mock_transform_data.assert_called_once_with(data, "12345")
        mock_get_httpx_client.return_value.post.assert_called_once()

    @patch('app.web.broker.broker.definedge.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.definedge.api.order_api.get_token')
    @patch('app.web.broker.broker.definedge.api.order_api.transform_data')
    def test_modify_order_api_error(self, mock_transform_data, mock_get_token, mock_get_httpx_client):
        mock_get_token.return_value = "12345"
        mock_transform_data.return_value = {"key": "value"}
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"stat": "Not_Ok", "emsg": "Invalid modification"}
        mock_response.text = json.dumps({"stat": "Not_Ok", "emsg": "Invalid modification"})
        mock_get_httpx_client.return_value.post.return_value = mock_response

        data = {"orderid": "ORD123", "exchange": "NSE", "new_quantity": "10"}
        res, response_data, orderid = modify_order(data, self.auth_token)

        self.assertIsNone(orderid)
        self.assertEqual(response_data, {"stat": "Not_Ok", "emsg": "Invalid modification"})
        self.assertEqual(res.status, 400)

    @patch('app.web.broker.broker.definedge.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.definedge.api.order_api.get_token')
    @patch('app.web.broker.broker.definedge.api.order_api.transform_data')
    @patch('app.web.broker.broker.definedge.api.order_api.logger')
    def test_modify_order_exception(self, mock_logger, mock_transform_data, mock_get_token, mock_get_httpx_client):
        mock_get_token.side_effect = Exception("Token error")
        data = {"orderid": "ORD123", "exchange": "NSE", "new_quantity": "10"}
        res, response_data, orderid = modify_order(data, self.auth_token)

        self.assertIsNone(orderid)
        self.assertEqual(response_data, {"stat": "Not_Ok", "emsg": "Error: Token error"})
        self.assertEqual(res.status, 500)
        mock_logger.error.assert_called_once()

    @patch('app.web.broker.broker.definedge.api.order_api.get_order_book')
    @patch('app.web.broker.broker.definedge.api.order_api.cancel_order')
    def test_cancel_all_orders_api_success(self, mock_cancel_order, mock_get_order_book):
        mock_get_order_book.return_value = {
            "stat": "Ok",
            "orders": [
                {"orderid": "ORD1", "exchange": "NSE", "status": "OPEN"},
                {"orderid": "ORD2", "exchange": "BSE", "status": "OPEN"}
            ]
        }
        mock_cancel_order.side_effect = [
            (MagicMock(status=200), {"stat": "Ok"}, "ORD1"),
            (MagicMock(status=200), {"stat": "Ok"}, "ORD2")
        ]

        response, status_code = cancel_all_orders_api(self.auth_token)

        self.assertEqual(status_code, 200)
        self.assertEqual(response, {"message": "All Open Orders Cancelled", "status": "success"})
        mock_get_order_book.assert_called_once_with(self.auth_token)
        self.assertEqual(mock_cancel_order.call_count, 2)

    @patch('app.web.broker.broker.definedge.api.order_api.get_order_book')
    @patch('app.web.broker.broker.definedge.api.order_api.cancel_order')
    def test_cancel_all_orders_api_no_open_orders(self, mock_cancel_order, mock_get_order_book):
        mock_get_order_book.return_value = {
            "stat": "Ok",
            "orders": [
                {"orderid": "ORD1", "exchange": "NSE", "status": "COMPLETE"}
            ]
        }

        response, status_code = cancel_all_orders_api(self.auth_token)

        self.assertEqual(status_code, 200)
        self.assertEqual(response, {"message": "No Open Orders to Cancel", "status": "success"})
        mock_get_order_book.assert_called_once_with(self.auth_token)
        mock_cancel_order.assert_not_called()

    @patch('app.web.broker.broker.definedge.api.order_api.get_order_book')
    def test_cancel_all_orders_api_get_order_book_error(self, mock_get_order_book):
        mock_get_order_book.return_value = {"stat": "Not_Ok", "emsg": "API Error"}

        response, status_code = cancel_all_orders_api(self.auth_token)

        self.assertEqual(status_code, 500)
        self.assertEqual(response, {"message": "Error fetching order book: API Error", "status": "error"})
        mock_get_order_book.assert_called_once_with(self.auth_token)

    @patch('app.web.broker.broker.definedge.api.order_api.get_order_book')
    @patch('app.web.broker.broker.definedge.api.order_api.cancel_order')
    def test_cancel_all_orders_api_partial_success(self, mock_cancel_order, mock_get_order_book):
        mock_get_order_book.return_value = {
            "stat": "Ok",
            "orders": [
                {"orderid": "ORD1", "exchange": "NSE", "status": "OPEN"},
                {"orderid": "ORD2", "exchange": "BSE", "status": "OPEN"}
            ]
        }
        mock_cancel_order.side_effect = [
            (MagicMock(status=200), {"stat": "Ok"}, "ORD1"),
            (MagicMock(status=400), {"stat": "Not_Ok", "emsg": "Failed"}, None)
        ]

        response, status_code = cancel_all_orders_api(self.auth_token)

        self.assertEqual(status_code, 500)
        self.assertEqual(response, {"message": "Some orders failed to cancel.", "status": "error"})
        mock_get_order_book.assert_called_once_with(self.auth_token)
        self.assertEqual(mock_cancel_order.call_count, 2)

    @patch('app.web.broker.broker.definedge.api.order_api.get_order_book', side_effect=Exception("Test Exception"))
    @patch('app.web.broker.broker.definedge.api.order_api.logger')
    def test_cancel_all_orders_api_exception(self, mock_logger, mock_get_order_book):
        response, status_code = cancel_all_orders_api(self.auth_token)

        self.assertEqual(status_code, 500)
        self.assertEqual(response, {"message": "Error cancelling all orders: Test Exception", "status": "error"})
        mock_get_order_book.assert_called_once_with(self.auth_token)
        mock_logger.error.assert_called_once()

    @patch('app.web.broker.broker.definedge.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.definedge.api.order_api.get_token')
    @patch('app.web.broker.broker.definedge.api.order_api.transform_data')
    def test_cancel_order_success(self, mock_transform_data, mock_get_token, mock_get_httpx_client):
        mock_get_token.return_value = "12345"
        mock_transform_data.return_value = {"key": "value"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stat": "Ok", "norenordno": "ORD123"}
        mock_response.text = json.dumps({"stat": "Ok", "norenordno": "ORD123"})
        mock_get_httpx_client.return_value.post.return_value = mock_response

        data = {"orderid": "ORD123", "exchange": "NSE"}
        res, response_data, orderid = cancel_order(data, self.auth_token)

        self.assertEqual(orderid, "ORD123")
        self.assertEqual(response_data, {"stat": "Ok", "norenordno": "ORD123"})
        self.assertEqual(res.status, 200)
        mock_get_token.assert_called_once_with(None, "NSE") # Symbol can be None for cancel order
        mock_transform_data.assert_called_once_with(data, "12345")
        mock_get_httpx_client.return_value.post.assert_called_once()

    @patch('app.web.broker.broker.definedge.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.definedge.api.order_api.get_token')
    @patch('app.web.broker.broker.definedge.api.order_api.transform_data')
    def test_cancel_order_api_error(self, mock_transform_data, mock_get_token, mock_get_httpx_client):
        mock_get_token.return_value = "12345"
        mock_transform_data.return_value = {"key": "value"}
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"stat": "Not_Ok", "emsg": "Invalid order id"}
        mock_response.text = json.dumps({"stat": "Not_Ok", "emsg": "Invalid order id"})
        mock_get_httpx_client.return_value.post.return_value = mock_response

        data = {"orderid": "ORD123", "exchange": "NSE"}
        res, response_data, orderid = cancel_order(data, self.auth_token)

        self.assertIsNone(orderid)
        self.assertEqual(response_data, {"stat": "Not_Ok", "emsg": "Invalid order id"})
        self.assertEqual(res.status, 400)

    @patch('app.web.broker.broker.definedge.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.definedge.api.order_api.get_token')
    @patch('app.web.broker.broker.definedge.api.order_api.transform_data')
    @patch('app.web.broker.broker.definedge.api.order_api.logger')
    def test_cancel_order_exception(self, mock_logger, mock_transform_data, mock_get_token, mock_get_httpx_client):
        mock_get_token.side_effect = Exception("Token error")
        data = {"orderid": "ORD123", "exchange": "NSE"}
        res, response_data, orderid = cancel_order(data, self.auth_token)

        self.assertIsNone(orderid)
        self.assertEqual(response_data, {"stat": "Not_Ok", "emsg": "Error: Token error"})
        self.assertEqual(res.status, 500)
        mock_logger.error.assert_called_once()

    @patch('app.web.broker.broker.definedge.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.definedge.api.order_api.get_token')
    @patch('app.web.broker.broker.definedge.api.order_api.transform_data')
    def test_modify_order_success(self, mock_transform_data, mock_get_token, mock_get_httpx_client):
        mock_get_token.return_value = "12345"
        mock_transform_data.return_value = {"key": "value"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stat": "Ok", "norenordno": "ORD123"}
        mock_response.text = json.dumps({"stat": "Ok", "norenordno": "ORD123"})
        mock_get_httpx_client.return_value.post.return_value = mock_response

        data = {"orderid": "ORD123", "exchange": "NSE", "new_quantity": "10"}
        res, response_data, orderid = modify_order(data, self.auth_token)

        self.assertEqual(orderid, "ORD123")
        self.assertEqual(response_data, {"stat": "Ok", "norenordno": "ORD123"})
        self.assertEqual(res.status, 200)
        mock_get_token.assert_called_once_with(None, "NSE") # Symbol can be None for modify order
        mock_transform_data.assert_called_once_with(data, "12345")
        mock_get_httpx_client.return_value.post.assert_called_once()

    @patch('app.web.broker.broker.definedge.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.definedge.api.order_api.get_token')
    @patch('app.web.broker.broker.definedge.api.order_api.transform_data')
    def test_modify_order_api_error(self, mock_transform_data, mock_get_token, mock_get_httpx_client):
        mock_get_token.return_value = "12345"
        mock_transform_data.return_value = {"key": "value"}
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"stat": "Not_Ok", "emsg": "Invalid modification"}
        mock_response.text = json.dumps({"stat": "Not_Ok", "emsg": "Invalid modification"})
        mock_get_httpx_client.return_value.post.return_value = mock_response

        data = {"orderid": "ORD123", "exchange": "NSE", "new_quantity": "10"}
        res, response_data, orderid = modify_order(data, self.auth_token)

        self.assertIsNone(orderid)
        self.assertEqual(response_data, {"stat": "Not_Ok", "emsg": "Invalid modification"})
        self.assertEqual(res.status, 400)

    @patch('app.web.broker.broker.definedge.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.definedge.api.order_api.get_token')
    @patch('app.web.broker.broker.definedge.api.order_api.transform_data')
    @patch('app.web.broker.broker.definedge.api.order_api.logger')
    def test_modify_order_exception(self, mock_logger, mock_transform_data, mock_get_token, mock_get_httpx_client):
        mock_get_token.side_effect = Exception("Token error")
        data = {"orderid": "ORD123", "exchange": "NSE", "new_quantity": "10"}
        res, response_data, orderid = modify_order(data, self.auth_token)

        self.assertIsNone(orderid)
        self.assertEqual(response_data, {"stat": "Not_Ok", "emsg": "Error: Token error"})
        self.assertEqual(res.status, 500)
        mock_logger.error.assert_called_once()

    @patch('app.web.broker.broker.definedge.api.order_api.get_order_book')
    @patch('app.web.broker.broker.definedge.api.order_api.cancel_order')
    def test_cancel_all_orders_api_success(self, mock_cancel_order, mock_get_order_book):
        mock_get_order_book.return_value = {
            "stat": "Ok",
            "orders": [
                {"orderid": "ORD1", "exchange": "NSE", "status": "OPEN"},
                {"orderid": "ORD2", "exchange": "BSE", "status": "OPEN"}
            ]
        }
        mock_cancel_order.side_effect = [
            (MagicMock(status=200), {"stat": "Ok"}, "ORD1"),
            (MagicMock(status=200), {"stat": "Ok"}, "ORD2")
        ]

        response, status_code = cancel_all_orders_api(self.auth_token)

        self.assertEqual(status_code, 200)
        self.assertEqual(response, {"message": "All Open Orders Cancelled", "status": "success"})
        mock_get_order_book.assert_called_once_with(self.auth_token)
        self.assertEqual(mock_cancel_order.call_count, 2)

    @patch('app.web.broker.broker.definedge.api.order_api.get_order_book')
    @patch('app.web.broker.broker.definedge.api.order_api.cancel_order')
    def test_cancel_all_orders_api_no_open_orders(self, mock_cancel_order, mock_get_order_book):
        mock_get_order_book.return_value = {
            "stat": "Ok",
            "orders": [
                {"orderid": "ORD1", "exchange": "NSE", "status": "COMPLETE"}
            ]
        }

        response, status_code = cancel_all_orders_api(self.auth_token)

        self.assertEqual(status_code, 200)
        self.assertEqual(response, {"message": "No Open Orders to Cancel", "status": "success"})
        mock_get_order_book.assert_called_once_with(self.auth_token)
        mock_cancel_order.assert_not_called()

    @patch('app.web.broker.broker.definedge.api.order_api.get_order_book')
    def test_cancel_all_orders_api_get_order_book_error(self, mock_get_order_book):
        mock_get_order_book.return_value = {"stat": "Not_Ok", "emsg": "API Error"}

        response, status_code = cancel_all_orders_api(self.auth_token)

        self.assertEqual(status_code, 500)
        self.assertEqual(response, {"message": "Error fetching order book: API Error", "status": "error"})
        mock_get_order_book.assert_called_once_with(self.auth_token)

    @patch('app.web.broker.broker.definedge.api.order_api.get_order_book')
    @patch('app.web.broker.broker.definedge.api.order_api.cancel_order')
    def test_cancel_all_orders_api_partial_success(self, mock_cancel_order, mock_get_order_book):
        mock_get_order_book.return_value = {
            "stat": "Ok",
            "orders": [
                {"orderid": "ORD1", "exchange": "NSE", "status": "OPEN"},
                {"orderid": "ORD2", "exchange": "BSE", "status": "OPEN"}
            ]
        }
        mock_cancel_order.side_effect = [
            (MagicMock(status=200), {"stat": "Ok"}, "ORD1"),
            (MagicMock(status=400), {"stat": "Not_Ok", "emsg": "Failed"}, None)
        ]

        response, status_code = cancel_all_orders_api(self.auth_token)

        self.assertEqual(status_code, 500)
        self.assertEqual(response, {"message": "Some orders failed to cancel.", "status": "error"})
        mock_get_order_book.assert_called_once_with(self.auth_token)
        self.assertEqual(mock_cancel_order.call_count, 2)

    @patch('app.web.broker.broker.definedge.api.order_api.get_order_book', side_effect=Exception("Test Exception"))
    @patch('app.web.broker.broker.definedge.api.order_api.logger')
    def test_cancel_all_orders_api_exception(self, mock_logger, mock_get_order_book):
        response, status_code = cancel_all_orders_api(self.auth_token)

        self.assertEqual(status_code, 500)
        self.assertEqual(response, {"message": "Error cancelling all orders: Test Exception", "status": "error"})
        mock_get_order_book.assert_called_once_with(self.auth_token)
        mock_logger.error.assert_called_once()
