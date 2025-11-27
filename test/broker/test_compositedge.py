import pytest
pytest.skip("Skipped by user request", allow_module_level=True)
from unittest.mock import patch, MagicMock
import pandas as pd

from app.core.brokers.compositedge.api.auth_api import authenticate_broker, get_feed_token
from app.core.brokers.compositedge.api.data import BrokerData

class TestCompositedgeIntegration:
    def setUp(self):
        self.auth_token = "dummy_auth_token"
        self.feed_token = "dummy_feed_token"
        self.user_id = "dummy_user_id"
        self.broker_data = BrokerData(self.auth_token, self.feed_token, self.user_id)

        # Mock settings for API keys
        self.mock_broker_api_key = "test_api_key"
        self.mock_broker_api_secret = "test_api_secret"
        self.mock_broker_api_key_market = "test_api_key_market"
        self.mock_broker_api_secret_market = "test_api_secret_market"

        # Patch settings for authentication
        patcher_api_key = patch('app.core.config.settings.BROKER_API_KEY', self.mock_broker_api_key)
        patcher_api_secret = patch('app.core.config.settings.BROKER_API_SECRET', self.mock_broker_api_secret)
        patcher_api_key_market = patch('app.core.config.settings.BROKER_API_KEY_MARKET', self.mock_broker_api_key_market)
        patcher_api_secret_market = patch('app.core.config.settings.BROKER_API_SECRET_MARKET', self.mock_broker_api_secret_market)

        self.mock_api_key = patcher_api_key.start()
        self.mock_api_secret = patcher_api_secret.start()
        self.mock_api_key_market = patcher_api_key_market.start()
        self.mock_api_secret_market = patcher_api_secret_market.start()

        self.addCleanup(patcher_api_key.stop)
        self.addCleanup(patcher_api_secret.stop)
        self.addCleanup(patcher_api_key_market.stop)
        self.addCleanup(patcher_api_secret_market.stop)

    @patch('app.web.broker.broker.compositedge.api.auth_api.get_httpx_client')
    @patch('app.web.broker.broker.compositedge.api.auth_api.get_feed_token')
    def test_authenticate_broker_success(self, mock_get_feed_token, mock_get_httpx_client):
        mock_client = MagicMock()
        mock_get_httpx_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "type": "success",
            "result": {"token": "new_auth_token"}
        }
        mock_client.post.return_value = mock_response

        mock_get_feed_token.return_value = ("new_feed_token", "new_user_id", None)

        request_token = "dummy_request_token"
        auth_token, feed_token, user_id, error = authenticate_broker(request_token)

        self.assertEqual(auth_token, "new_auth_token")
        self.assertEqual(feed_token, "new_feed_token")
        self.assertEqual(user_id, "new_user_id")
        self.assertIsNone(error)
        mock_client.post.assert_called_once()
        mock_get_feed_token.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.auth_api.get_httpx_client')
    @patch('app.web.broker.broker.compositedge.api.auth_api.get_feed_token')
    def test_authenticate_broker_failure(self, mock_get_feed_token, mock_get_httpx_client):
        mock_client = MagicMock()
        mock_get_httpx_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "type": "error",
            "description": "Invalid credentials"
        }
        mock_client.post.return_value = mock_response

        mock_get_feed_token.return_value = (None, None, "feed token error")

        request_token = "dummy_request_token"
        auth_token, feed_token, user_id, error = authenticate_broker(request_token)

        self.assertIsNone(auth_token)
        self.assertIsNone(feed_token)
        self.assertIsNone(user_id)
        self.assertIsNotNone(error)
        self.assertIn("API error", error)
        mock_client.post.assert_called_once()
        mock_get_feed_token.assert_not_called()

    @patch('app.web.broker.broker.compositedge.api.auth_api.get_httpx_client')
    @patch('app.web.broker.broker.compositedge.api.auth_api.get_feed_token')
    def test_authenticate_broker_exception(self, mock_get_feed_token, mock_get_httpx_client):
        mock_get_httpx_client.side_effect = Exception("Network error")

        request_token = "dummy_request_token"
        auth_token, feed_token, user_id, error = authenticate_broker(request_token)

        self.assertIsNone(auth_token)
        self.assertIsNone(feed_token)
        self.assertIsNone(user_id)
        self.assertIsNotNone(error)
        self.assertIn("Error during authentication", error)
        mock_get_feed_token.assert_not_called()

    @patch('app.web.broker.broker.compositedge.api.auth_api.get_httpx_client')
    def test_get_feed_token_success(self, mock_get_httpx_client):
        mock_client = MagicMock()
        mock_get_httpx_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "type": "success",
            "result": {"token": "new_feed_token", "userID": "new_user_id"}
        }
        mock_client.post.return_value = mock_response

        feed_token, user_id, error = get_feed_token()

        self.assertEqual(feed_token, "new_feed_token")
        self.assertEqual(user_id, "new_user_id")
        self.assertIsNone(error)
        mock_client.post.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.auth_api.get_httpx_client')
    def test_get_feed_token_failure(self, mock_get_httpx_client):
        mock_client = MagicMock()
        mock_get_httpx_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "type": "error",
            "description": "Invalid market credentials"
        }
        mock_client.post.return_value = mock_response

        feed_token, user_id, error = get_feed_token()

        self.assertIsNone(feed_token)
        self.assertIsNone(user_id)
        self.assertIsNotNone(error)
        self.assertIn("API Error (Feed)", error)
        mock_client.post.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.auth_api.get_httpx_client')
    def test_get_feed_token_exception(self, mock_get_httpx_client):
        mock_get_httpx_client.side_effect = Exception("Feed network error")

        feed_token, user_id, error = get_feed_token()

        self.assertIsNone(feed_token)
        self.assertIsNone(user_id)
        self.assertIsNotNone(error)
        self.assertIn("An exception occurred", error)

    @patch('app.web.broker.broker.compositedge.api.data.db_session')
    @patch('app.web.broker.broker.compositedge.api.data.get_br_symbol')
    def test_get_instrument_token_success(self, mock_get_br_symbol, mock_db_session):
        mock_get_br_symbol.return_value = "BR_SYMBOL"
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = MagicMock(token="INSTRUMENT_TOKEN")

        symbol_info, brexchange = self.broker_data._get_instrument_token("SYMBOL", "NSE")

        self.assertEqual(symbol_info.token, "INSTRUMENT_TOKEN")
        self.assertEqual(brexchange, 1)
        mock_get_br_symbol.assert_called_once_with("SYMBOL", "NSE")
        mock_db_session.assert_called_once()
        mock_session.query.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.data.db_session')
    @patch('app.web.broker.broker.compositedge.api.data.get_br_symbol')
    def test_get_instrument_token_unknown_exchange(self, mock_get_br_symbol, mock_db_session):
        mock_get_br_symbol.return_value = "BR_SYMBOL"

        with self.assertRaisesRegex(Exception, "Unknown exchange segment: UNKNOWN"):
            self.broker_data._get_instrument_token("SYMBOL", "UNKNOWN")

        mock_get_br_symbol.assert_called_once_with("SYMBOL", "UNKNOWN")
        mock_db_session.assert_not_called()

    @patch('app.web.broker.broker.compositedge.api.data.db_session')
    @patch('app.web.broker.broker.compositedge.api.data.get_br_symbol')
    def test_get_instrument_token_not_found(self, mock_get_br_symbol, mock_db_session):
        mock_get_br_symbol.return_value = "BR_SYMBOL"
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        with self.assertRaisesRegex(Exception, "Could not find exchange token for NSE:BR_SYMBOL"):
            self.broker_data._get_instrument_token("SYMBOL", "NSE")

        mock_get_br_symbol.assert_called_once_with("SYMBOL", "NSE")
        mock_db_session.assert_called_once()
        mock_session.query.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.data.get_api_response')
    def test_fetch_market_data_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"listQuotes": ['{"Touchline": {"LastTradedPrice": 100}}']}
        }

        token_info = {"exchangeSegment": 1, "exchangeInstrumentID": "TOKEN"}
        market_data = self.broker_data._fetch_market_data(token_info, 1502)

        self.assertEqual(market_data['Touchline']['LastTradedPrice'], 100)
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.data.get_api_response')
    def test_fetch_market_data_api_error(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "error",
            "description": "API Error"
        }

        token_info = {"exchangeSegment": 1, "exchangeInstrumentID": "TOKEN"}
        market_data = self.broker_data._fetch_market_data(token_info, 1502)

        self.assertIsNone(market_data)
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.data.get_api_response')
    def test_fetch_market_data_empty_list_quotes(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"listQuotes": []}
        }

        token_info = {"exchangeSegment": 1, "exchangeInstrumentID": "TOKEN"}
        market_data = self.broker_data._fetch_market_data(token_info, 1502)

        self.assertIsNone(market_data)
        mock_get_api_response.assert_called_once()

    @patch.object(BrokerData, '_get_instrument_token')
    @patch.object(BrokerData, '_fetch_market_data')
    def test_get_quotes_success(self, mock_fetch_market_data, mock_get_instrument_token):
        mock_get_instrument_token.return_value = (MagicMock(token="INSTRUMENT_TOKEN"), 1)
        mock_fetch_market_data.side_effect = [
            {"Touchline": {"AskInfo": {"Price": 101}, "BidInfo": {"Price": 99}, "High": 105, "Low": 95,
                           "LastTradedPrice": 100, "Open": 98, "Close": 97, "TotalTradedQuantity": 1000}},
            {"OpenInterest": 500}
        ]

        quotes = self.broker_data.get_quotes("SYMBOL", "NSE")

        self.assertEqual(quotes['ltp'], 100)
        self.assertEqual(quotes['oi'], 500)
        self.assertEqual(quotes['ask'], 101)
        self.assertEqual(quotes['bid'], 99)
        mock_get_instrument_token.assert_called_once_with("SYMBOL", "NSE")
        self.assertEqual(mock_fetch_market_data.call_count, 2)

    @patch.object(BrokerData, '_get_instrument_token')
    @patch.object(BrokerData, '_fetch_market_data')
    def test_get_quotes_market_data_failure(self, mock_fetch_market_data, mock_get_instrument_token):
        mock_get_instrument_token.return_value = (MagicMock(token="INSTRUMENT_TOKEN"), 1)
        mock_fetch_market_data.return_value = None

        with self.assertRaisesRegex(Exception, "Failed to fetch market data"):
            self.broker_data.get_quotes("SYMBOL", "NSE")

        mock_get_instrument_token.assert_called_once_with("SYMBOL", "NSE")
        mock_fetch_market_data.assert_called_once_with({"exchangeSegment": 1, "exchangeInstrumentID": "INSTRUMENT_TOKEN"}, 1502)

    @patch.object(BrokerData, '_get_instrument_token')
    @patch.object(BrokerData, '_fetch_market_data')
    def test_get_quotes_exception(self, mock_fetch_market_data, mock_get_instrument_token):
        mock_get_instrument_token.side_effect = Exception("Instrument token error")

        with self.assertRaisesRegex(Exception, "Instrument token error"):
            self.broker_data.get_quotes("SYMBOL", "NSE")

        mock_get_instrument_token.assert_called_once_with("SYMBOL", "NSE")
        mock_fetch_market_data.assert_not_called()

    @patch('app.web.broker.broker.compositedge.api.data.db_session')
    @patch('app.web.broker.broker.compositedge.api.data.get_br_symbol')
    @patch('app.web.broker.broker.compositedge.api.data.get_api_response')
    @patch('pandas.to_datetime')
    @patch('pandas.DataFrame')
    @patch('pandas.concat')
    def test_get_history_success(self, mock_concat, mock_dataframe, mock_to_datetime, mock_get_api_response, mock_get_br_symbol, mock_db_session):
        mock_get_br_symbol.return_value = "BR_SYMBOL"
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = MagicMock(token="INSTRUMENT_TOKEN")

        mock_to_datetime.side_effect = [
            pd.Timestamp('2023-01-01 00:00:00', tz='Asia/Kolkata'),
            pd.Timestamp('2023-01-07 00:00:00', tz='Asia/Kolkata'),
        ]

        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"dataReponse": "1672534800|100|105|95|102|1000,1672621200|102|108|98|105|1200"}
        }

        mock_df_instance = MagicMock()
        mock_dataframe.return_value = mock_df_instance
        mock_concat.return_value = mock_df_instance

        result = self.broker_data.get_history("SYMBOL", "NSE", "1D", "2023-01-01", "2023-01-07")

        self.assertIsNotNone(result)
        mock_get_br_symbol.assert_called_once_with("SYMBOL", "NSE")
        mock_db_session.assert_called_once()
        mock_get_api_response.assert_called_once()
        mock_dataframe.assert_called()
        mock_concat.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.data.db_session')
    @patch('app.web.broker.broker.compositedge.api.data.get_br_symbol')
    def test_get_history_unsupported_timeframe(self, mock_get_br_symbol, mock_db_session):
        with self.assertRaisesRegex(Exception, "Unsupported timeframe: 2h"):
            self.broker_data.get_history("SYMBOL", "NSE", "2h", "2023-01-01", "2023-01-07")
        mock_get_br_symbol.assert_not_called()
        mock_db_session.assert_not_called()

    @patch('app.web.broker.broker.compositedge.api.data.db_session')
    @patch('app.web.broker.broker.compositedge.api.data.get_br_symbol')
    @patch('app.web.broker.broker.compositedge.api.data.get_api_response')
    @patch('pandas.to_datetime')
    def test_get_history_api_error(self, mock_to_datetime, mock_get_api_response, mock_get_br_symbol, mock_db_session):
        mock_get_br_symbol.return_value = "BR_SYMBOL"
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = MagicMock(token="INSTRUMENT_TOKEN")

        mock_to_datetime.side_effect = [
            pd.Timestamp('2023-01-01 00:00:00', tz='Asia/Kolkata'),
            pd.Timestamp('2023-01-07 00:00:00', tz='Asia/Kolkata'),
        ]

        mock_get_api_response.return_value = {
            "type": "error",
            "description": "API Error"
        }

        with self.assertRaisesRegex(Exception, "Error from CompositEdge API: API Error"):
            self.broker_data.get_history("SYMBOL", "NSE", "1D", "2023-01-01", "2023-01-07")

        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.data.db_session')
    @patch('app.web.broker.broker.compositedge.api.data.get_br_symbol')
    def test_get_history_exception(self, mock_get_br_symbol, mock_db_session):
        mock_get_br_symbol.side_effect = Exception("Symbol conversion error")

        with self.assertRaisesRegex(Exception, "Symbol conversion error"):
            self.broker_data.get_history("SYMBOL", "NSE", "1D", "2023-01-01", "2023-01-07")

        mock_get_br_symbol.assert_called_once_with("SYMBOL", "NSE")
        mock_db_session.assert_not_called()

    @patch('app.web.broker.broker.compositedge.api.data.get_api_response')
    def test_get_market_depth_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {
                "marketDepth": {
                    "buy": [{"price": 100, "quantity": 10}, {"price": 99, "quantity": 20}],
                    "sell": [{"price": 101, "quantity": 15}, {"price": 102, "quantity": 25}]
                }
            }
        }
        result = self.broker_data.get_market_depth("INSTRUMENT_TOKEN", "NSE")
        self.assertIsNotNone(result)
        self.assertIn("buy", result)
        self.assertIn("sell", result)
        self.assertEqual(len(result["buy"]), 2)
        self.assertEqual(result["buy"][0]["price"], 100)
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.data.get_api_response')
    def test_get_market_depth_api_error(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "error",
            "description": "API Error"
        }
        with self.assertRaisesRegex(Exception, "Error fetching market depth: API Error"):
            self.broker_data.get_market_depth("INSTRUMENT_TOKEN", "NSE")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.data.get_api_response')
    def test_get_market_depth_exception(self, mock_get_api_response):
        mock_get_api_response.side_effect = Exception("Network error")
        with self.assertRaisesRegex(Exception, "Error fetching market depth: Network error"):
            self.broker_data.get_market_depth("INSTRUMENT_TOKEN", "NSE")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.data.db_session')
    @patch('app.web.broker.broker.compositedge.api.data.get_br_symbol')
    @patch('app.web.broker.broker.compositedge.api.data.BrokerData.get_market_depth')
    def test_get_depth_success(self, mock_get_market_depth, mock_get_br_symbol, mock_db_session):
        mock_get_br_symbol.return_value = "BR_SYMBOL"
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = MagicMock(token="INSTRUMENT_TOKEN")

        mock_get_market_depth.return_value = {
            "buy": [{"price": 100, "quantity": 10, "orders": 1}, {"price": 99, "quantity": 20, "orders": 2}],
            "sell": [{"price": 101, "quantity": 15, "orders": 1}, {"price": 102, "quantity": 25, "orders": 2}]
        }

        result = self.broker_data.get_depth("SYMBOL", "NSE")
        self.assertIsNotNone(result)
        self.assertIn("buy", result)
        self.assertIn("sell", result)
        self.assertEqual(len(result["buy"]), 2)
        self.assertEqual(result["buy"][0]["price"], 100)
        mock_get_br_symbol.assert_called_once_with("SYMBOL", "NSE")
        mock_get_market_depth.assert_called_once_with("INSTRUMENT_TOKEN", "NSE")

    @patch('app.web.broker.broker.compositedge.api.data.db_session')
    @patch('app.web.broker.broker.compositedge.api.data.get_br_symbol')
    def test_get_depth_instrument_token_not_found(self, mock_get_br_symbol, mock_db_session):
        mock_get_br_symbol.return_value = "BR_SYMBOL"
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        with self.assertRaisesRegex(Exception, "Instrument token not found for SYMBOL on NSE"):
            self.broker_data.get_depth("SYMBOL", "NSE")

        mock_get_br_symbol.assert_called_once_with("SYMBOL", "NSE")
        mock_db_session.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.data.db_session')
    @patch('app.web.broker.broker.compositedge.api.data.get_br_symbol')
    @patch('app.web.broker.broker.compositedge.api.data.BrokerData.get_market_depth')
    def test_get_depth_market_depth_error(self, mock_get_market_depth, mock_get_br_symbol, mock_db_session):
        mock_get_br_symbol.return_value = "BR_SYMBOL"
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = MagicMock(token="INSTRUMENT_TOKEN")

        mock_get_market_depth.side_effect = Exception("Market depth API error")

        with self.assertRaisesRegex(Exception, "Market depth API error"):
            self.broker_data.get_depth("SYMBOL", "NSE")

        mock_get_br_symbol.assert_called_once_with("SYMBOL", "NSE")
        mock_get_market_depth.assert_called_once_with("INSTRUMENT_TOKEN", "NSE")

    @patch('app.web.broker.broker.compositedge.api.data.db_session')
    @patch('app.web.broker.broker.compositedge.api.data.get_br_symbol')
    def test_get_depth_exception(self, mock_get_br_symbol, mock_db_session):
        mock_get_br_symbol.side_effect = Exception("Symbol conversion error")

        with self.assertRaisesRegex(Exception, "Symbol conversion error"):
            self.broker_data.get_depth("SYMBOL", "NSE")

        mock_get_br_symbol.assert_called_once_with("SYMBOL", "NSE")
        mock_db_session.assert_not_called()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_get_order_book_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": [
                {"order_id": "1", "symbol": "TEST", "status": "COMPLETE"},
                {"order_id": "2", "symbol": "TEST2", "status": "PENDING"}
            ]
        }
        result = self.broker_data.get_order_book()
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["order_id"], "1")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_get_order_book_api_error(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "error",
            "description": "API Error"
        }
        with self.assertRaisesRegex(Exception, "Error fetching order book: API Error"):
            self.broker_data.get_order_book()
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_get_trade_book_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": [
                {"trade_id": "T1", "symbol": "TEST", "quantity": 10},
                {"trade_id": "T2", "symbol": "TEST2", "quantity": 20}
            ]
        }
        result = self.broker_data.get_trade_book()
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["trade_id"], "T1")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_get_trade_book_api_error(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "error",
            "description": "API Error"
        }
        with self.assertRaisesRegex(Exception, "Error fetching trade book: API Error"):
            self.broker_data.get_trade_book()
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_get_trade_book_exception(self, mock_get_api_response):
        mock_get_api_response.side_effect = Exception("Network error")
        with self.assertRaisesRegex(Exception, "Error fetching trade book: Network error"):
            self.broker_data.get_trade_book()
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_get_positions_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": [
                {"symbol": "TEST", "quantity": 10, "type": "BUY"},
                {"symbol": "TEST2", "quantity": 5, "type": "SELL"}
            ]
        }
        result = self.broker_data.get_positions()
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["symbol"], "TEST")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_get_positions_api_error(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "error",
            "description": "API Error"
        }
        with self.assertRaisesRegex(Exception, "Error fetching positions: API Error"):
            self.broker_data.get_positions()
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker/broker.compositedge.api.order_api.get_api_response')
    def test_get_positions_exception(self, mock_get_api_response):
        mock_get_api_response.side_effect = Exception("Network error")
        with self.assertRaisesRegex(Exception, "Error fetching positions: Network error"):
            self.broker_data.get_positions()
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_get_holdings_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": [
                {"symbol": "TEST", "quantity": 10, "avg_price": 100},
                {"symbol": "TEST2", "quantity": 5, "avg_price": 200}
            ]
        }
        result = self.broker_data.get_holdings()
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["symbol"], "TEST")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_get_holdings_api_error(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "error",
            "description": "API Error"
        }
        with self.assertRaisesRegex(Exception, "Error fetching holdings: API Error"):
            self.broker_data.get_holdings()
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_get_holdings_exception(self, mock_get_api_response):
        mock_get_api_response.side_effect = Exception("Network error")
        with self.assertRaisesRegex(Exception, "Error fetching holdings: Network error"):
            self.broker_data.get_holdings()
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_get_open_position_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": [
                {"symbol": "TEST", "quantity": 10, "type": "BUY"},
                {"symbol": "TEST2", "quantity": 5, "type": "SELL"}
            ]
        }
        result = self.broker_data.get_open_position("TEST", "NSE")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["symbol"], "TEST")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_get_open_position_api_error(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "error",
            "description": "API Error"
        }
        with self.assertRaisesRegex(Exception, "Error fetching open position: API Error"):
            self.broker_data.get_open_position("TEST", "NSE")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_get_open_position_exception(self, mock_get_api_response):
        mock_get_api_response.side_effect = Exception("Network error")
        with self.assertRaisesRegex(Exception, "Error fetching open position: Network error"):
            self.broker_data.get_open_position("TEST", "NSE")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_place_order_api_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"norenordno": "ORDER123"}
        }
        order_params = {"symbol": "TEST", "qty": 1, "price": 100}
        response, order_id = self.broker_data.place_order_api(order_params)
        self.assertIsNotNone(response)
        self.assertEqual(order_id, "ORDER123")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_place_order_api_api_error(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "error",
            "description": "API Error"
        }
        order_params = {"symbol": "TEST", "qty": 1, "price": 100}
        with self.assertRaisesRegex(Exception, "Error placing order: API Error"):
            self.broker_data.place_order_api(order_params)
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_place_order_api_exception(self, mock_get_api_response):
        mock_get_api_response.side_effect = Exception("Network error")
        order_params = {"symbol": "TEST", "qty": 1, "price": 100}
        with self.assertRaisesRegex(Exception, "Error placing order: Network error"):
            self.broker_data.place_order_api(order_params)
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_place_smartorder_api_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"norenordno": "SMARTORDER123"}
        }
        order_params = {"symbol": "TEST", "qty": 1, "price": 100}
        response, order_id = self.broker_data.place_smartorder_api(order_params)
        self.assertIsNotNone(response)
        self.assertEqual(order_id, "SMARTORDER123")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_place_smartorder_api_api_error(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "error",
            "description": "API Error"
        }
        order_params = {"symbol": "TEST", "qty": 1, "price": 100}
        with self.assertRaisesRegex(Exception, "Error placing smart order: API Error"):
            self.broker_data.place_smartorder_api(order_params)
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_place_smartorder_api_exception(self, mock_get_api_response):
        mock_get_api_response.side_effect = Exception("Network error")
        order_params = {"symbol": "TEST", "qty": 1, "price": 100}
        with self.assertRaisesRegex(Exception, "Error placing smart order: Network error"):
            self.broker_data.place_smartorder_api(order_params)
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_close_all_positions_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"message": "All positions closed successfully"}
        }
        response = self.broker_data.close_all_positions()
        self.assertIsNotNone(response)
        self.assertEqual(response["message"], "All positions closed successfully")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_close_all_positions_api_error(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "error",
            "description": "API Error"
        }
        with self.assertRaisesRegex(Exception, "Error closing all positions: API Error"):
            self.broker_data.close_all_positions()
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_close_all_positions_exception(self, mock_get_api_response):
        mock_get_api_response.side_effect = Exception("Network error")
        with self.assertRaisesRegex(Exception, "Error closing all positions: Network error"):
            self.broker_data.close_all_positions()
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_cancel_order_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"message": "Order cancelled successfully"}
        }
        response = self.broker_data.cancel_order("ORDER123")
        self.assertIsNotNone(response)
        self.assertEqual(response["message"], "Order cancelled successfully")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_cancel_order_api_error(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "error",
            "description": "API Error"
        }
        with self.assertRaisesRegex(Exception, "Error cancelling order: API Error"):
            self.broker_data.cancel_order("ORDER123")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_cancel_order_exception(self, mock_get_api_response):
        mock_get_api_response.side_effect = Exception("Network error")
        with self.assertRaisesRegex(Exception, "Error cancelling order: Network error"):
            self.broker_data.cancel_order("ORDER123")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_get_order_book_exception(self, mock_get_api_response):
        mock_get_api_response.side_effect = Exception("Network error")
        with self.assertRaisesRegex(Exception, "Error fetching order book: Network error"):
            self.broker_data.get_order_book()
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_modify_order_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"message": "Order modified successfully"}
        }
        order_params = {"order_id": "ORDER123", "new_qty": 2}
        response = self.broker_data.modify_order(order_params)
        self.assertIsNotNone(response)
        self.assertEqual(response["message"], "Order modified successfully")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_modify_order_api_error(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "error",
            "description": "API Error"
        }
        order_params = {"order_id": "ORDER123", "new_qty": 2}
        with self.assertRaisesRegex(Exception, "Error modifying order: API Error"):
            self.broker_data.modify_order(order_params)
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_modify_order_exception(self, mock_get_api_response):
        mock_get_api_response.side_effect = Exception("Network error")
        order_params = {"order_id": "ORDER123", "new_qty": 2}
        with self.assertRaisesRegex(Exception, "Error modifying order: Network error"):
            self.broker_data.modify_order(order_params)
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_cancel_all_orders_api_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "success",
            "result": {"message": "All orders cancelled successfully"}
        }
        response = self.broker_data.cancel_all_orders_api()
        self.assertIsNotNone(response)
        self.assertEqual(response["message"], "All orders cancelled successfully")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_cancel_all_orders_api_api_error(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "type": "error",
            "description": "API Error"
        }
        with self.assertRaisesRegex(Exception, "Error cancelling all orders: API Error"):
            self.broker_data.cancel_all_orders_api()
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.order_api.get_api_response')
    def test_cancel_all_orders_api_exception(self, mock_get_api_response):
        mock_get_api_response.side_effect = Exception("Network error")
        with self.assertRaisesRegex(Exception, "Error cancelling all orders: Network error"):
            self.broker_data.cancel_all_orders_api()
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.compositedge.api.data.get_api_response')
    def test_fetch_market_data_exception(self, mock_get_api_response):
        mock_get_api_response.side_effect = Exception("Network error")

        token_info = {"exchangeSegment": 1, "exchangeInstrumentID": "TOKEN"}
        market_data = self.broker_data._fetch_market_data(token_info, 1502)

        self.assertIsNone(market_data)
        mock_get_api_response.assert_called_once()
