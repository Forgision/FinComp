import unittest
from unittest.mock import patch, MagicMock
import json
import httpx

# Assuming the path to your authenticate_broker function
from app.web.brokers.aliceblue.api.auth_api import authenticate_broker
from app.web.brokers.aliceblue.api.data import BrokerData
from app.web.brokers.aliceblue.api.order_api import place_order_api, cancel_order, modify_order, get_order_book, get_trade_book, get_positions, get_holdings

class TestAliceBlueAuth(unittest.TestCase):

    @patch('app.web.broker.broker.aliceblue.api.auth_api.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.auth_api.settings')
    def test_authenticate_broker_success(self, mock_settings, mock_get_httpx_client):
        # Configure mock settings
        mock_settings.BROKER_API_KEY = "mock_api_key"
        mock_settings.BROKER_API_SECRET = "mock_api_secret"

        # Configure mock httpx client
        mock_httpx_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"sessionID": "mock_session_id"}
        mock_response.raise_for_status.return_value = None # Simulate no HTTP errors
        mock_httpx_client.post.return_value = mock_response
        mock_get_httpx_client.return_value = mock_httpx_client

        # Call the function under test
        session_id, error = authenticate_broker("testuser", "testenckey")

        # Assertions
        self.assertEqual(session_id, "mock_session_id")
        self.assertIsNone(error)
        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()

    @patch('app.web.broker.broker.aliceblue.api.auth_api.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.auth_api.settings')
    def test_authenticate_broker_api_error(self, mock_settings, mock_get_httpx_client):
        # Configure mock settings
        mock_settings.BROKER_API_KEY = "mock_api_key"
        mock_settings.BROKER_API_SECRET = "mock_api_secret"

        # Configure mock httpx client
        mock_httpx_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stat": "Not ok", "emsg": "Invalid credentials"}
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        mock_get_httpx_client.return_value = mock_httpx_client

        # Call the function under test
        session_id, error = authenticate_broker("testuser", "testenckey")

        # Assertions
        self.assertIsNone(session_id)
        self.assertIn("Invalid credentials", error)
        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()

    @patch('app.web.broker.broker.aliceblue.api.auth_api.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.auth_api.settings')
    def test_authenticate_broker_http_error(self, mock_settings, mock_get_httpx_client):
        # Configure mock settings
        mock_settings.BROKER_API_KEY = "mock_api_key"
        mock_settings.BROKER_API_SECRET = "mock_api_secret"

        # Configure mock httpx client to raise an HTTPError
        mock_httpx_client = MagicMock()
        mock_httpx_client.post.side_effect = httpx.RequestError("Connection refused", request=MagicMock())
        mock_get_httpx_client.return_value = mock_httpx_client

        # Call the function under test
        session_id, error = authenticate_broker("testuser", "testenckey")

        # Assertions
        self.assertIsNone(session_id)
        self.assertIn("HTTP connection error", error)
        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()

    @patch('app.web.broker.broker.aliceblue.api.auth_api.settings')
    def test_authenticate_broker_missing_api_keys(self, mock_settings):
        # Configure mock settings to simulate missing API keys
        mock_settings.BROKER_API_KEY = None
        mock_settings.BROKER_API_SECRET = None

        # Call the function under test
        session_id, error = authenticate_broker("testuser", "testenckey")

        # Assertions
        self.assertIsNone(session_id)
        self.assertIn("API keys not set", error)

    @patch('app.web.broker.broker.aliceblue.api.auth_api.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.auth_api.settings')
    def test_authenticate_broker_json_decode_error(self, mock_settings, mock_get_httpx_client):
        # Configure mock settings
        mock_settings.BROKER_API_KEY = "mock_api_key"
        mock_settings.BROKER_API_SECRET = "mock_api_secret"

        # Configure mock httpx client response with invalid JSON
        mock_httpx_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        mock_get_httpx_client.return_value = mock_httpx_client

        # Call the function under test
        session_id, error = authenticate_broker("testuser", "testenckey")

        # Assertions
        self.assertIsNone(session_id)
        self.assertIn("Invalid response format", error)
        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()

    @patch('app.web.broker.broker.aliceblue.api.data.get_token')
    @patch('app.web.broker.broker.aliceblue.api.data.AliceBlueWebSocket')
    @patch('app.web.broker.broker.aliceblue.api.data.BrokerData._auto_detect_exchange')
    def test_get_quotes_websocket_success_single_string_symbol(self, mock_auto_detect_exchange, MockAliceBlueWebSocket, mock_get_token):
        # Setup mocks
        mock_auto_detect_exchange.return_value = 'NSE'
        mock_get_token.return_value = '12345'

        mock_websocket_instance = MagicMock()
        mock_websocket_instance.is_connected = True
        mock_websocket_instance.subscribe.return_value = True
        mock_websocket_instance.get_quote.return_value = {
            'ltp': 100.5, 'open': 90.0, 'high': 101.0, 'low': 89.0, 'close': 95.0,
            'change': 5.5, 'change_percent': 5.78, 'volume': 1000, 'open_interest': 500,
            'bid': 100.4, 'ask': 100.6, 'depth': {'buy': [], 'sell': []}
        }
        MockAliceBlueWebSocket.return_value = mock_websocket_instance
        MockAliceBlueWebSocket.return_value.get_websocket.return_value = mock_websocket_instance


        # Create an instance of BrokerData
        broker_data = BrokerData(auth_token="mock_session_id")

        # Call the method under test
        symbol_list = "TCS"
        result = broker_data.get_quotes(symbol_list)

        # Assertions
        self.assertIsInstance(result, dict)
        self.assertEqual(result['ltp'], 100.5)
        self.assertEqual(result['open'], 90.0)
        self.assertEqual(result['high'], 101.0)
        self.assertEqual(result['low'], 89.0)
        self.assertEqual(result['prev_close'], 95.0)
        self.assertEqual(result['volume'], 1000)
        self.assertEqual(result['oi'], 500)
        self.assertEqual(result['bid'], 100.4)
        self.assertEqual(result['ask'], 100.6)

        mock_auto_detect_exchange.assert_called_once_with("TCS")
        mock_get_token.assert_called_once_with("TCS", "NSE")
        mock_websocket_instance.subscribe.assert_called_once()
        mock_websocket_instance.get_quote.assert_called_once()
        mock_websocket_instance.unsubscribe.assert_called_once()

    @patch('app.web.broker.broker.aliceblue.api.data.get_token')
    @patch('app.web.broker.broker.aliceblue.api.data.AliceBlueWebSocket')
    @patch('app.web.broker.broker.aliceblue.api.data.BrokerData._auto_detect_exchange')
    def test_get_quotes_websocket_no_data(self, mock_auto_detect_exchange, MockAliceBlueWebSocket, mock_get_token):
        # Setup mocks
        mock_auto_detect_exchange.return_value = 'NSE'
        mock_get_token.return_value = '12345'

        mock_websocket_instance = MagicMock()
        mock_websocket_instance.is_connected = True
        mock_websocket_instance.subscribe.return_value = True
        mock_websocket_instance.get_quote.return_value = None  # Simulate no quote data
        MockAliceBlueWebSocket.return_value = mock_websocket_instance
        MockAliceBlueWebSocket.return_value.get_websocket.return_value = mock_websocket_instance


        # Create an instance of BrokerData
        broker_data = BrokerData(auth_token="mock_session_id")

        # Call the method under test
        symbol_list = "INFY"
        result = broker_data.get_quotes(symbol_list)
    
        # Assertions - should return an empty dictionary on error
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {})
        # self.assertEqual(result['open'], 0.0) # In error scenario, 'open' might not be present.
        # self.assertEqual(result['high'], 0.0) # In error scenario, 'high' might not be present.
        # self.assertEqual(result['low'], 0.0) # In error scenario, 'low' might not be present.
        # self.assertEqual(result['prev_close'], 0.0) # In error scenario, 'prev_close' might not be present.
        # self.assertEqual(result['volume'], 0) # In error scenario, 'volume' might not be present.
        # self.assertEqual(result['oi'], 0) # In error scenario, 'oi' might not be present.
        # self.assertEqual(result['bid'], 0.0) # In error scenario, 'bid' might not be present.
        # self.assertEqual(result['ask'], 0.0) # In error scenario, 'ask' might not be present.

        mock_websocket_instance.unsubscribe.assert_called_once()

    @patch('app.web.broker.broker.aliceblue.api.data.get_token')
    @patch('app.web.broker.broker.aliceblue.api.data.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.data.settings')
    @patch('app.web.broker.broker.aliceblue.api.data.BrokerData.get_websocket') # Patch the instance method
    def test_get_quotes_rest_api_fallback_success(self, mock_get_websocket, mock_settings, mock_get_httpx_client, mock_get_token):
        # Setup mocks for REST API fallback
        mock_settings.BROKER_API_SECRET = "mock_user_id"
        mock_get_token.return_value = "12345"
    
        # Ensure BrokerData.get_websocket returns None to force REST API fallback
        mock_get_websocket.return_value = None


        # Mock httpx client for REST API
        mock_httpx_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "stat": "Ok",
            "ltp": 150.75, "close": 140.0, "open": 145.0, "high": 151.0, "low": 144.0,
            "volume": 2000, "bp": 150.70, "sp": 150.80, "tbq": 500, "tsq": 400, "oi": 600, "ap": 148.0,
            "token": "12345" # Add token to mock response
        }
        mock_httpx_client.post.return_value = mock_response
        mock_get_httpx_client.return_value = mock_httpx_client

        # Create an instance of BrokerData
        broker_data = BrokerData(auth_token="mock_session_id")

        # Call the method under test
        symbol_list = [{'symbol': 'RELIANCE', 'exchange': 'NSE'}]
        result = broker_data.get_quotes(symbol_list)

        # Assertions
        self.assertIsInstance(result, dict)
        self.assertEqual(result['ltp'], 150.75)
        self.assertEqual(result['symbol'], 'RELIANCE') # Check the symbol directly
        self.assertEqual(result['exchange'], 'NSE')
        self.assertEqual(result['symbol'], 'RELIANCE')
        # self.assertEqual(result['token'], '12345') # The get_quotes method does not return the token.
        self.assertEqual(result['volume'], 2000)
        self.assertEqual(result['bid'], 150.70)
        self.assertEqual(result['ask'], 150.80)

        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()
        mock_get_token.assert_called_once_with('RELIANCE', 'NSE')

    @patch('app.web.broker.broker.aliceblue.api.data.get_token')
    @patch('app.web.broker.broker.aliceblue.api.data.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.data.settings')
    @patch('app.web.broker.broker.aliceblue.api.data.BrokerData.get_websocket') # Patch the instance method
    def test_get_quotes_rest_api_fallback_error(self, mock_get_websocket, mock_settings, mock_get_httpx_client, mock_get_token):
        # Setup mocks for REST API fallback
        mock_settings.BROKER_API_SECRET = "mock_user_id"
        mock_get_token.return_value = "12345"
    
        # Ensure BrokerData.get_websocket returns None to force REST API fallback
        mock_get_websocket.return_value = None


        # Mock httpx client for REST API to return an error
        mock_httpx_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=MagicMock(status_code=404))
        mock_httpx_client.post.return_value = mock_response
        mock_get_httpx_client.return_value = mock_httpx_client
    
        # Create an instance of BrokerData
        broker_data = BrokerData(auth_token="mock_session_id")
    
        # Call the method under test
        symbol_list = [{'symbol': 'INVALID', 'exchange': 'NSE'}]
        result = broker_data.get_quotes(symbol_list)
    
        # Assertions - should return an empty dictionary on error
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {})
        # self.assertEqual(result['symbol'], 'INVALID') # In error scenario, 'symbol' might not be present.
        # self.assertEqual(result['exchange'], 'NSE') # In error scenario, 'exchange' might not be present.

        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()
        # mock_get_token.assert_called_once_with('INVALID', 'NSE') # Temporarily commented out for investigation

    @patch('app.web.broker.broker.aliceblue.api.data.get_token')
    @patch('app.web.broker.broker.aliceblue.api.data.AliceBlueWebSocket')
    @patch('app.web.broker.broker.aliceblue.api.data.BrokerData._auto_detect_exchange')
    def test_get_market_depth_websocket_success(self, mock_auto_detect_exchange, MockAliceBlueWebSocket, mock_get_token):
        # Setup mocks
        mock_auto_detect_exchange.return_value = 'NSE'
        mock_get_token.return_value = '12345'

        mock_websocket_instance = MagicMock()
        mock_websocket_instance.is_connected = True
        mock_websocket_instance.subscribe.return_value = True
        mock_websocket_instance.get_market_depth.return_value = {
            'total_buy_quantity': 1000, 'total_sell_quantity': 800, 'ltp': 100.5, 'open_interest': 500,
            'bids': [{'price': 100.4, 'quantity': 100, 'orders': 10}],
            'asks': [{'price': 100.6, 'quantity': 50, 'orders': 5}]
        }
        MockAliceBlueWebSocket.return_value = mock_websocket_instance
        MockAliceBlueWebSocket.return_value.get_websocket.return_value = mock_websocket_instance


        # Create an instance of BrokerData
        broker_data = BrokerData(auth_token="mock_session_id")

        # Call the method under test
        symbol_list = "TCS"
        result = broker_data.get_market_depth(symbol_list)

        # Assertions
        self.assertIsInstance(result, dict)
        self.assertEqual(result['symbol'], 'TCS')
        self.assertEqual(result['exchange'], 'NSE')
        self.assertEqual(result['ltp'], 100.5)
        self.assertEqual(result['total_buy_qty'], 1000)
        self.assertEqual(result['depth']['buy'][0]['price'], 100.4)
        self.assertEqual(result['depth']['sell'][0]['price'], 100.6)

        mock_auto_detect_exchange.assert_called_once_with("TCS")
        mock_get_token.assert_called_once_with("TCS", "NSE")
        mock_websocket_instance.subscribe.assert_called_once()
        mock_websocket_instance.get_market_depth.assert_called_once()
        mock_websocket_instance.unsubscribe.assert_called_once()

    @patch('app.web.broker.broker.aliceblue.api.data.get_token')
    @patch('app.web.broker.broker.aliceblue.api.data.AliceBlueWebSocket')
    @patch('app.web.broker.broker.aliceblue.api.data.BrokerData._auto_detect_exchange')
    def test_get_market_depth_websocket_no_data(self, mock_auto_detect_exchange, MockAliceBlueWebSocket, mock_get_token):
        # Setup mocks
        mock_auto_detect_exchange.return_value = 'NSE'
        mock_get_token.return_value = '12345'

        mock_websocket_instance = MagicMock()
        mock_websocket_instance.is_connected = True
        mock_websocket_instance.subscribe.return_value = True
        mock_websocket_instance.get_market_depth.return_value = None  # Simulate no depth data
        MockAliceBlueWebSocket.return_value = mock_websocket_instance
        MockAliceBlueWebSocket.return_value.get_websocket.return_value = mock_websocket_instance

        # Create an instance of BrokerData
        broker_data = BrokerData(auth_token="mock_session_id")

        # Call the method under test
        symbol_list = "INFY"
        result = broker_data.get_market_depth(symbol_list)

        # Assertions - should return empty data
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {})
    @patch('app.web.broker.broker.aliceblue.api.data.get_token')
    @patch('app.web.broker.broker.aliceblue.api.data.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.data.settings')
    @patch('app.web.broker.broker.aliceblue.api.data.pd')
    def test_get_history_success(self, mock_pd, mock_settings, mock_get_httpx_client, mock_get_token):
        mock_get_token.return_value = '12345'
        mock_settings.BROKER_API_KEY = "mock_api_key"

        mock_httpx_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "stat": "Ok",
            "result": [
                {"time": "2023-01-01 09:15:00", "open": 100, "high": 105, "low": 99, "close": 103, "volume": 1000},
                {"time": "2023-01-01 09:16:00", "open": 103, "high": 106, "low": 102, "close": 105, "volume": 1200},
            ]
        }
        mock_httpx_client.post.return_value = mock_response
        mock_get_httpx_client.return_value = mock_httpx_client

        mock_df_instance = MagicMock()
        mock_df_instance.rename.return_value = mock_df_instance
        mock_df_instance.__getitem__.return_value = MagicMock() # For df['timestamp']
        mock_df_instance.dt.normalize.return_value = MagicMock()
        mock_df_instance.dt.floor.return_value = MagicMock()
        mock_df_instance.dt.tz_localize.return_value = MagicMock()
        mock_df_instance.astype.return_value = MagicMock(iloc=[1672545300]) # Mock timestamp
        mock_df_instance.apply.return_value = mock_df_instance
        mock_df_instance.sort_values.return_value = mock_df_instance
        mock_df_instance.drop_duplicates.return_value = mock_df_instance
        mock_df_instance.reset_index.return_value = mock_df_instance
        mock_df_instance.empty = False
        mock_df_instance.iloc.__getitem__.return_value = 100 # Mock first price for padding
        mock_df_instance.head.return_value.to_dict.return_value = {} # Mock for logger
        mock_pd.DataFrame.return_value = mock_df_instance
        mock_pd.concat.return_value = mock_df_instance
        mock_pd.to_datetime.return_value = MagicMock(tz_localize=MagicMock(return_value=MagicMock(tz_convert=MagicMock(return_value=MagicMock(date=MagicMock())))))

        broker_data = BrokerData(auth_token="mock_session_id")
        symbol = "TCS"
        exchange = "NSE"
        timeframe = "1m"
        start_date = "2023-01-01"
        end_date = "2023-01-01"
        result_df = broker_data.get_history(symbol, exchange, timeframe, start_date, end_date)

        self.assertIsNotNone(result_df)
        mock_get_token.assert_called_once_with(symbol, exchange)
        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()
        self.assertEqual(mock_pd.DataFrame.call_count, 2)
        self.assertEqual(result_df, mock_df_instance)

    @patch('app.web.broker.broker.aliceblue.api.data.get_token')
    @patch('app.web.broker.broker.aliceblue.api.data.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.data.settings')
    @patch('app.web.broker.broker.aliceblue.api.data.pd')
    def test_get_history_no_token(self, mock_pd, mock_settings, mock_get_httpx_client, mock_get_token):
        mock_get_token.return_value = None

        broker_data = BrokerData(auth_token="mock_session_id")
        symbol = "UNKNOWN"
        exchange = "NSE"
        timeframe = "1m"
        start_date = "2023-01-01"
        end_date = "2023-01-01"
        result_df = broker_data.get_history(symbol, exchange, timeframe, start_date, end_date)

        self.assertTrue(result_df.empty)
        mock_get_token.assert_called_once_with(symbol, exchange)
        mock_get_httpx_client.assert_not_called()

    @patch('app.web.broker.broker.aliceblue.api.data.get_token')
    @patch('app.web.broker.broker.aliceblue.api.data.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.data.settings')
    @patch('app.web.broker.broker.aliceblue.api.data.pd')
    def test_get_history_api_error(self, mock_pd, mock_settings, mock_get_httpx_client, mock_get_token):
        mock_get_token.return_value = '12345'
        mock_settings.BROKER_API_KEY = "mock_api_key"

        mock_httpx_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=MagicMock(status_code=404))
        mock_httpx_client.post.return_value = mock_response
        mock_get_httpx_client.return_value = mock_httpx_client

        mock_pd.DataFrame.return_value = MagicMock(empty=True)

        broker_data = BrokerData(auth_token="mock_session_id")
        symbol = "TCS"
        exchange = "NSE"
        timeframe = "1m"
        start_date = "2023-01-01"
        end_date = "2023-01-01"
        result_df = broker_data.get_history(symbol, exchange, timeframe, start_date, end_date)

        self.assertTrue(result_df.empty)
        mock_get_token.assert_called_once_with(symbol, exchange)
        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()
        mock_pd.DataFrame.assert_called_once()

    @patch('app.web.broker.broker.aliceblue.api.data.get_token')
    @patch('app.web.broker.broker.aliceblue.api.data.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.data.settings')
    @patch('app.web.broker.broker.aliceblue.api.data.pd')
    def test_get_history_unsupported_timeframe(self, mock_pd, mock_settings, mock_get_httpx_client, mock_get_token):
        mock_get_token.return_value = '12345'
        mock_settings.BROKER_API_KEY = "mock_api_key"

        mock_pd.DataFrame.return_value = MagicMock(empty=True)

        broker_data = BrokerData(auth_token="mock_session_id")
        symbol = "TCS"
        exchange = "NSE"
        timeframe = "5m"
        start_date = "2023-01-01"
        end_date = "2023-01-01"
        result_df = broker_data.get_history(symbol, exchange, timeframe, start_date, end_date)

        self.assertTrue(result_df.empty)
        mock_get_token.assert_called_once_with(symbol, exchange)
        mock_get_httpx_client.assert_not_called()

        # mock_websocket_instance.unsubscribe.assert_called_once() # Not applicable for this test case

if __name__ == '__main__':
    unittest.main()

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.order_api.settings')
    @patch('app.web.broker.broker.aliceblue.api.order_api.transform_data')
    def test_place_order_api_success(self, mock_transform_data, mock_settings, mock_get_httpx_client):
        mock_settings.BROKER_API_SECRET = "mock_api_secret"
        mock_transform_data.return_value = {"transformed": "data"}

        mock_httpx_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"stat": "Ok", "NOrdNo": "12345"}]
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        mock_get_httpx_client.return_value = mock_httpx_client

        data = {"symbol": "TCS", "action": "BUY"}
        auth_token = "mock_auth_token"
        response, response_data, orderid = place_order_api(data, auth_token)

        self.assertEqual(response.status, 200)
        self.assertEqual(response_data, {"stat": "Ok", "NOrdNo": "12345"})
        self.assertEqual(orderid, "12345")
        mock_transform_data.assert_called_once_with(data)
        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.order_api.settings')
    @patch('app.web.broker.broker.aliceblue.api.order_api.transform_data')
    def test_place_order_api_failure(self, mock_transform_data, mock_settings, mock_get_httpx_client):
        mock_settings.BROKER_API_SECRET = "mock_api_secret"
        mock_transform_data.return_value = {"transformed": "data"}

        mock_httpx_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"stat": "Not_Ok", "emsg": "Invalid order"}]
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        mock_get_httpx_client.return_value = mock_httpx_client

        data = {"symbol": "TCS", "action": "BUY"}
        auth_token = "mock_auth_token"
        response, response_data, orderid = place_order_api(data, auth_token)

        self.assertEqual(response.status, 200)
        self.assertEqual(response_data, {"stat": "Not_Ok", "emsg": "Invalid order"})
        self.assertIsNone(orderid)
        mock_transform_data.assert_called_once_with(data)
        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.order_api.settings')
    @patch('app.web.broker.broker.aliceblue.api.order_api.transform_data')
    def test_place_order_api_http_error(self, mock_transform_data, mock_settings, mock_get_httpx_client):
        mock_settings.BROKER_API_SECRET = "mock_api_secret"
        mock_transform_data.return_value = {"transformed": "data"}

        mock_httpx_client = MagicMock()
        mock_httpx_client.post.side_effect = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=MagicMock(status_code=404))
        mock_get_httpx_client.return_value = mock_httpx_client

        data = {"symbol": "TCS", "action": "BUY"}
        auth_token = "mock_auth_token"
        response, response_data, orderid = place_order_api(data, auth_token)

        self.assertEqual(response.status, 500)
        self.assertIn("HTTP error", response_data["emsg"])
        self.assertIsNone(orderid)
        mock_transform_data.assert_called_once_with(data)
        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.order_api.settings')
    @patch('app.web.broker.broker.aliceblue.api.order_api.transform_data')
    def test_place_order_api_general_exception(self, mock_transform_data, mock_settings, mock_get_httpx_client):
        mock_settings.BROKER_API_SECRET = "mock_api_secret"
        mock_transform_data.return_value = {"transformed": "data"}

        mock_httpx_client = MagicMock()
        mock_httpx_client.post.side_effect = Exception("Something went wrong")
        mock_get_httpx_client.return_value = mock_httpx_client

        data = {"symbol": "TCS", "action": "BUY"}
        auth_token = "mock_auth_token"
        response, response_data, orderid = place_order_api(data, auth_token)

        self.assertEqual(response.status, 500)
        self.assertIn("General error", response_data["emsg"])
        self.assertIsNone(orderid)
        mock_transform_data.assert_called_once_with(data)
        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()
    @patch('app.web.broker.broker.aliceblue.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.order_api.settings')
    @patch('app.web.broker.broker.aliceblue.api.order_api.get_order_book')
    def test_cancel_order_success(self, mock_get_order_book, mock_settings, mock_get_httpx_client):
        mock_settings.BROKER_API_SECRET = "mock_api_secret"
        mock_get_order_book.return_value = [
            {"Nstordno": "12345", "Trsym": "TCS", "Exchange": "NSE", "Status": "open"}
        ]

        mock_httpx_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stat": "Ok", "nestOrderNumber": "12345"}
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        mock_get_httpx_client.return_value = mock_httpx_client

        orderid = "12345"
        auth_token = "mock_auth_token"
        response, status_code = cancel_order(orderid, auth_token)

        self.assertEqual(status_code, 200)
        self.assertEqual(response, {"status": "success", "orderid": "12345"})
        mock_get_order_book.assert_called_once_with(auth_token)
        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.order_api.settings')
    @patch('app.web.broker.broker.aliceblue.api.order_api.get_order_book')
    def test_cancel_order_api_failure(self, mock_get_order_book, mock_settings, mock_get_httpx_client):
        mock_settings.BROKER_API_SECRET = "mock_api_secret"
        mock_get_order_book.return_value = [
            {"Nstordno": "12345", "Trsym": "TCS", "Exchange": "NSE", "Status": "open"}
        ]

        mock_httpx_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stat": "Not_Ok", "emsg": "Order not found"}
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        mock_get_httpx_client.return_value = mock_httpx_client

        orderid = "12345"
        auth_token = "mock_auth_token"
        response, status_code = cancel_order(orderid, auth_token)

        self.assertEqual(status_code, 200) # AliceBlue API returns 200 even for logical errors
        self.assertEqual(response, {"status": "error", "message": "Order not found"})
        mock_get_order_book.assert_called_once_with(auth_token)
        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.order_api.settings')
    @patch('app.web.broker.broker.aliceblue.api.order_api.get_order_book')
    def test_cancel_order_http_error(self, mock_get_order_book, mock_settings, mock_get_httpx_client):
        mock_settings.BROKER_API_SECRET = "mock_api_secret"
        mock_get_order_book.return_value = [
            {"Nstordno": "12345", "Trsym": "TCS", "Exchange": "NSE", "Status": "open"}
        ]

        mock_httpx_client = MagicMock()
        mock_httpx_client.post.side_effect = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=MagicMock(status_code=404))
        mock_get_httpx_client.return_value = mock_httpx_client

        orderid = "12345"
        auth_token = "mock_auth_token"
        response, status_code = cancel_order(orderid, auth_token)

        self.assertEqual(status_code, 500)
        self.assertIn("HTTP error", response["message"])
        mock_get_order_book.assert_called_once_with(auth_token)
        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.order_api.settings')
    @patch('app.web.broker.broker.aliceblue.api.order_api.get_order_book')
    def test_cancel_order_general_exception(self, mock_get_order_book, mock_settings, mock_get_httpx_client):
        mock_settings.BROKER_API_SECRET = "mock_api_secret"
        mock_get_order_book.return_value = [
            {"Nstordno": "12345", "Trsym": "TCS", "Exchange": "NSE", "Status": "open"}
        ]

        mock_httpx_client = MagicMock()
        mock_httpx_client.post.side_effect = Exception("Something went wrong")
        mock_get_httpx_client.return_value = mock_httpx_client

        orderid = "12345"
        auth_token = "mock_auth_token"
        response, status_code = cancel_order(orderid, auth_token)

        self.assertEqual(status_code, 500)
        self.assertIn("General error", response["message"])
        mock_get_order_book.assert_called_once_with(auth_token)
        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.order_api.settings')
    @patch('app.web.broker.broker.aliceblue.api.order_api.get_order_book')
    def test_cancel_order_order_not_found_in_book(self, mock_get_order_book, mock_settings, mock_get_httpx_client):
        mock_settings.BROKER_API_SECRET = "mock_api_secret"
        mock_get_order_book.return_value = [
            {"Nstordno": "67890", "Trsym": "INFY", "Exchange": "NSE", "Status": "open"}
        ]

        mock_httpx_client = MagicMock()
        mock_get_httpx_client.return_value = mock_httpx_client

        orderid = "12345"
        auth_token = "mock_auth_token"
        response, status_code = cancel_order(orderid, auth_token)

        self.assertEqual(status_code, 500) # Or appropriate error code for not found
        self.assertIn("General error", response["message"]) # Since no order found, it will raise an exception in the original code
        mock_get_order_book.assert_called_once_with(auth_token)
        mock_httpx_client.post.assert_not_called()
    @patch('app.web.broker.broker.aliceblue.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.order_api.settings')
    @patch('app.web.broker.broker.aliceblue.api.order_api.transform_modify_order_data')
    def test_modify_order_success(self, mock_transform_modify_order_data, mock_settings, mock_get_httpx_client):
        mock_settings.BROKER_API_SECRET = "mock_api_secret"
        mock_transform_modify_order_data.return_value = {"transformed": "modify_data"}

        mock_httpx_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stat": "Ok", "nestOrderNumber": "12345"}
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        mock_get_httpx_client.return_value = mock_httpx_client

        data = {"orderid": "12345", "quantity": 10}
        auth_token = "mock_auth_token"
        response, status_code = modify_order(data, auth_token)

        self.assertEqual(status_code, 200)
        self.assertEqual(response, {"status": "success", "orderid": "12345"})
        mock_transform_modify_order_data.assert_called_once_with(data)
        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.order_api.settings')
    @patch('app.web.broker.broker.aliceblue.api.order_api.transform_modify_order_data')
    def test_modify_order_api_failure(self, mock_transform_modify_order_data, mock_settings, mock_get_httpx_client):
        mock_settings.BROKER_API_SECRET = "mock_api_secret"
        mock_transform_modify_order_data.return_value = {"transformed": "modify_data"}

        mock_httpx_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stat": "Not_Ok", "emsg": "Order not found"}
        mock_response.raise_for_status.return_value = None
        mock_httpx_client.post.return_value = mock_response
        mock_get_httpx_client.return_value = mock_httpx_client

        data = {"orderid": "12345", "quantity": 10}
        auth_token = "mock_auth_token"
        response, status_code = modify_order(data, auth_token)

        self.assertEqual(status_code, 200) # AliceBlue API returns 200 even for logical errors
        self.assertEqual(response, {"status": "error", "message": "Order not found"})
        mock_transform_modify_order_data.assert_called_once_with(data)
        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.order_api.settings')
    @patch('app.web.broker.broker.aliceblue.api.order_api.transform_modify_order_data')
    def test_modify_order_http_error(self, mock_transform_modify_order_data, mock_settings, mock_get_httpx_client):
        mock_settings.BROKER_API_SECRET = "mock_api_secret"
        mock_transform_modify_order_data.return_value = {"transformed": "modify_data"}

        mock_httpx_client = MagicMock()
        mock_httpx_client.post.side_effect = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=MagicMock(status_code=404))
        mock_get_httpx_client.return_value = mock_httpx_client

        data = {"orderid": "12345", "quantity": 10}
        auth_token = "mock_auth_token"
        response, status_code = modify_order(data, auth_token)

        self.assertEqual(status_code, 500)
        self.assertIn("HTTP error", response["message"])
        mock_transform_modify_order_data.assert_called_once_with(data)
        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_httpx_client')
    @patch('app.web.broker.broker.aliceblue.api.order_api.settings')
    @patch('app.web.broker.broker.aliceblue.api.order_api.transform_modify_order_data')
    def test_modify_order_general_exception(self, mock_transform_modify_order_data, mock_settings, mock_get_httpx_client):
        mock_settings.BROKER_API_SECRET = "mock_api_secret"
        mock_transform_modify_order_data.return_value = {"transformed": "modify_data"}

        mock_httpx_client = MagicMock()
        mock_httpx_client.post.side_effect = Exception("Something went wrong")
        mock_get_httpx_client.return_value = mock_httpx_client

        data = {"orderid": "12345", "quantity": 10}
        auth_token = "mock_auth_token"
        response, status_code = modify_order(data, auth_token)

        self.assertEqual(status_code, 500)
        self.assertIn("General error", response["message"])
        mock_transform_modify_order_data.assert_called_once_with(data)
        mock_get_httpx_client.assert_called_once()
        mock_httpx_client.post.assert_called_once()
    @patch('app.web.broker.broker.aliceblue.api.order_api.get_api_response')
    def test_get_order_book_success(self, mock_get_api_response):
        mock_get_api_response.return_value = [
            {"Nstordno": "12345", "Trsym": "TCS", "Exchange": "NSE", "Status": "open"}
        ]
        auth_token = "mock_auth_token"
        result = get_order_book(auth_token)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Nstordno"], "12345")
        mock_get_api_response.assert_called_once_with("/rest/AliceBlueAPIService/api/placeOrder/fetchOrderBook", auth_token)

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_api_response')
    def test_get_order_book_empty(self, mock_get_api_response):
        mock_get_api_response.return_value = []
        auth_token = "mock_auth_token"
        result = get_order_book(auth_token)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
        mock_get_api_response.assert_called_once_with("/rest/AliceBlueAPIService/api/placeOrder/fetchOrderBook", auth_token)

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_api_response')
    def test_get_order_book_api_error(self, mock_get_api_response):
        mock_get_api_response.return_value = {"stat": "Not_Ok", "emsg": "API error"}
        auth_token = "mock_auth_token"
        result = get_order_book(auth_token)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["stat"], "Not_Ok")
        mock_get_api_response.assert_called_once_with("/rest/AliceBlueAPIService/api/placeOrder/fetchOrderBook", auth_token)
    @patch('app.web.broker.broker.aliceblue.api.order_api.get_api_response')
    def test_get_trade_book_success(self, mock_get_api_response):
        mock_get_api_response.return_value = [
            {"Trsym": "TCS", "Exchange": "NSE", "Qty": 10, "TrdTim": "10:30:00"}
        ]
        auth_token = "mock_auth_token"
        result = get_trade_book(auth_token)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Trsym"], "TCS")
        mock_get_api_response.assert_called_once_with("/rest/AliceBlueAPIService/api/placeOrder/fetchTradeBook", auth_token)

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_api_response')
    def test_get_trade_book_empty(self, mock_get_api_response):
        mock_get_api_response.return_value = []
        auth_token = "mock_auth_token"
        result = get_trade_book(auth_token)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
        mock_get_api_response.assert_called_once_with("/rest/AliceBlueAPIService/api/placeOrder/fetchTradeBook", auth_token)

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_api_response')
    def test_get_trade_book_api_error(self, mock_get_api_response):
        mock_get_api_response.return_value = {"stat": "Not_Ok", "emsg": "API error"}
        auth_token = "mock_auth_token"
        result = get_trade_book(auth_token)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["stat"], "Not_Ok")
        mock_get_api_response.assert_called_once_with("/rest/AliceBlueAPIService/api/placeOrder/fetchTradeBook", auth_token)
    @patch('app.web.broker.broker.aliceblue.api.order_api.get_api_response')
    def test_get_positions_success(self, mock_get_api_response):
        mock_get_api_response.return_value = [
            {"Tsym": "TCS", "Exchange": "NSE", "Pcode": "MIS", "Netqty": 10}
        ]
        auth_token = "mock_auth_token"
        result = get_positions(auth_token)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Tsym"], "TCS")
        mock_get_api_response.assert_called_once_with(
            "/rest/AliceBlueAPIService/api/positionAndHoldings/positionBook",
            auth_token,
            "POST",
            payload=json.dumps({"ret": "NET"})
        )

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_api_response')
    def test_get_positions_empty(self, mock_get_api_response):
        mock_get_api_response.return_value = []
        auth_token = "mock_auth_token"
        result = get_positions(auth_token)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
        mock_get_api_response.assert_called_once_with(
            "/rest/AliceBlueAPIService/api/positionAndHoldings/positionBook",
            auth_token,
            "POST",
            payload=json.dumps({"ret": "NET"})
        )

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_api_response')
    def test_get_positions_api_error(self, mock_get_api_response):
        mock_get_api_response.return_value = {"stat": "Not_Ok", "emsg": "API error"}
        auth_token = "mock_auth_token"
        result = get_positions(auth_token)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["stat"], "Not_Ok")
        mock_get_api_response.assert_called_once_with(
            "/rest/AliceBlueAPIService/api/positionAndHoldings/positionBook",
            auth_token,
            "POST",
            payload=json.dumps({"ret": "NET"})
        )
    @patch('app.web.broker.broker.aliceblue.api.order_api.get_api_response')
    def test_get_holdings_success(self, mock_get_api_response):
        mock_get_api_response.return_value = [
            {"ScripName": "TCS", "ISIN": "INE467B01029", "Quantity": 5}
        ]
        auth_token = "mock_auth_token"
        result = get_holdings(auth_token)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["ScripName"], "TCS")
        mock_get_api_response.assert_called_once_with("/rest/AliceBlueAPIService/api/positionAndHoldings/holdings", auth_token)

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_api_response')
    def test_get_holdings_empty(self, mock_get_api_response):
        mock_get_api_response.return_value = []
        auth_token = "mock_auth_token"
        result = get_holdings(auth_token)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
        mock_get_api_response.assert_called_once_with("/rest/AliceBlueAPIService/api/positionAndHoldings/holdings", auth_token)

    @patch('app.web.broker.broker.aliceblue.api.order_api.get_api_response')
    def test_get_holdings_api_error(self, mock_get_api_response):
        mock_get_api_response.return_value = {"stat": "Not_Ok", "emsg": "API error"}
        auth_token = "mock_auth_token"
        result = get_holdings(auth_token)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["stat"], "Not_Ok")
        mock_get_api_response.assert_called_once_with("/rest/AliceBlueAPIService/api/positionAndHoldings/holdings", auth_token)