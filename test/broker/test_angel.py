import unittest
from unittest.mock import patch, MagicMock

from app.web.broker.broker.angel.api.auth_api import authenticate_broker
from app.web.broker.broker.angel.api.data import BrokerData
from app.web.broker.broker.angel.api.order_api import (
    get_order_book, get_trade_book, get_positions, get_holdings,
    place_order_api, place_smartorder_api, close_all_positions,
    cancel_order, modify_order, cancel_all_orders_api
)
import pandas as pd # Import pandas for DataFrame assertions
# from app.web.broker.broker.angel.api.order_api import place_order_api


class TestAngelIntegration(unittest.TestCase):

    def setUp(self):
        self.auth_token = "dummy_auth_token"
        self.broker_data = BrokerData(self.auth_token)

    @patch('app.web.broker.broker.angel.api.auth_api.get_httpx_client')
    def test_authenticate_broker_success(self, mock_get_httpx_client):
        mock_client = MagicMock()
        mock_get_httpx_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"data": {"jwtToken": "mock_jwt_token", "feedToken": "mock_feed_token"}, "message": "SUCCESS"}'
        mock_client.post.return_value = mock_response

        auth_token, feed_token, error = authenticate_broker("test_client", "test_pin", "123456")

        self.assertEqual(auth_token, "mock_jwt_token")
        self.assertEqual(feed_token, "mock_feed_token")
        self.assertIsNone(error)
        mock_client.post.assert_called_once()

    @patch('app.web.broker.broker.angel.api.auth_api.get_httpx_client')
    def test_authenticate_broker_failure(self, mock_get_httpx_client):
        mock_client = MagicMock()
        mock_get_httpx_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"message": "Invalid credentials"}'
        mock_client.post.return_value = mock_response

        auth_token, feed_token, error = authenticate_broker("wrong_client", "wrong_pin", "000000")

        self.assertIsNone(auth_token)
        self.assertIsNone(feed_token)
        self.assertEqual(error, "Invalid credentials")
        mock_client.post.assert_called_once()

    @patch('app.web.broker.broker.angel.api.auth_api.get_httpx_client')
    def test_authenticate_broker_exception(self, mock_get_httpx_client):
        mock_get_httpx_client.side_effect = Exception("Network error")

        auth_token, feed_token, error = authenticate_broker("test_client", "test_pin", "123456")

        self.assertIsNone(auth_token)
        self.assertIsNone(feed_token)
        self.assertEqual(error, "Network error")
        mock_get_httpx_client.assert_called_once()

    @patch('app.web.broker.broker.angel.api.data.get_br_symbol')
    @patch('app.web.broker.broker.angel.api.data.get_token')
    @patch('app.web.broker.broker.angel.api.data.get_api_response')
    def test_get_quotes_success(self, mock_get_api_response, mock_get_token, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "ANGEL_SYMBOL"
        mock_get_token.return_value = "ANGEL_TOKEN"
        mock_get_api_response.return_value = {
            "status": True,
            "data": {
                "fetched": [
                    {
                        "depth": {
                            "buy": [{"price": 100.0, "quantity": 100}],
                            "sell": [{"price": 101.0, "quantity": 100}]
                        },
                        "open": 99.0,
                        "high": 102.0,
                        "low": 98.0,
                        "ltp": 100.5,
                        "close": 99.5,
                        "tradeVolume": 1000,
                        "opnInterest": 500
                    }
                ]
            }
        }

        quotes = self.broker_data.get_quotes("TESTSYMBOL", "NSE")

        self.assertEqual(quotes['bid'], 100.0)
        self.assertEqual(quotes['ask'], 101.0)
        self.assertEqual(quotes['open'], 99.0)
        self.assertEqual(quotes['high'], 102.0)
        self.assertEqual(quotes['low'], 98.0)
        self.assertEqual(quotes['ltp'], 100.5)
        self.assertEqual(quotes['prev_close'], 99.5)
        self.assertEqual(quotes['volume'], 1000)
        self.assertEqual(quotes['oi'], 500)
        mock_get_br_symbol.assert_called_once_with("TESTSYMBOL", "NSE")
        mock_get_token.assert_called_once_with("TESTSYMBOL", "NSE")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.angel.api.data.get_br_symbol')
    @patch('app.web.broker.broker.angel.api.data.get_token')
    @patch('app.web.broker.broker.angel.api.data.get_api_response')
    def test_get_quotes_api_error(self, mock_get_api_response, mock_get_token, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "ANGEL_SYMBOL"
        mock_get_token.return_value = "ANGEL_TOKEN"
        mock_get_api_response.return_value = {
            "status": False,
            "message": "API error message"
        }

        with self.assertRaisesRegex(Exception, "Error from Angel API: API error message"):
            self.broker_data.get_quotes("TESTSYMBOL", "NSE")

    @patch('app.web.broker.broker.angel.api.data.get_br_symbol')
    @patch('app.web.broker.broker.angel.api.data.get_token')
    @patch('app.web.broker.broker.angel.api.data.get_api_response')
    def test_get_quotes_no_data(self, mock_get_api_response, mock_get_token, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "ANGEL_SYMBOL"
        mock_get_token.return_value = "ANGEL_TOKEN"
        mock_get_api_response.return_value = {
            "status": True,
            "data": {"fetched": []}
        }

        with self.assertRaisesRegex(Exception, "No quote data received"):
            self.broker_data.get_quotes("TESTSYMBOL", "NSE")

    @patch('app.web.broker.broker.angel.api.data.get_br_symbol', side_effect=Exception("Symbol error"))
    def test_get_quotes_exception(self, mock_get_br_symbol):
        with self.assertRaisesRegex(Exception, "Error fetching quotes: Symbol error"):
            self.broker_data.get_quotes("TESTSYMBOL", "NSE")

    @patch('app.web.broker.broker.angel.api.data.get_br_symbol')
    @patch('app.web.broker.broker.angel.api.data.get_token')
    @patch('app.web.broker.broker.angel.api.data.get_api_response')
    def test_get_history_success(self, mock_get_api_response, mock_get_token, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "ANGEL_SYMBOL"
        mock_get_token.return_value = "ANGEL_TOKEN"
        mock_get_api_response.return_value = {
            "status": True,
            "data": [
                ["2023-01-01T09:15:00.000Z", 100, 105, 99, 104, 1000],
                ["2023-01-01T09:20:00.000Z", 104, 106, 103, 105, 1200]
            ]
        }
        # Mock get_oi_history to return an empty DataFrame or specific data if needed
        with patch.object(self.broker_data, 'get_oi_history', return_value=pd.DataFrame(columns=['timestamp', 'oi'])):
            df = self.broker_data.get_history("TESTSYMBOL", "NSE", "5m", "2023-01-01", "2023-01-01")

            self.assertIsInstance(df, pd.DataFrame)
            self.assertFalse(df.empty)
            self.assertEqual(len(df), 2)
            self.assertEqual(df.iloc[0]['open'], 100)
            self.assertEqual(df.iloc[1]['volume'], 1200)
            self.assertIn('oi', df.columns)
            mock_get_br_symbol.assert_called_once_with("TESTSYMBOL", "NSE")
            mock_get_token.assert_called_once_with("TESTSYMBOL", "NSE")
            mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.angel.api.data.get_br_symbol')
    @patch('app.web.broker.broker.angel.api.data.get_token')
    @patch('app.web.broker.broker.angel.api.data.get_api_response')
    def test_get_history_unsupported_interval(self, mock_get_api_response, mock_get_token, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "ANGEL_SYMBOL"
        mock_get_token.return_value = "ANGEL_TOKEN"
        with self.assertRaisesRegex(Exception, "Timeframe '2m' is not supported by Angel."):
            self.broker_data.get_history("TESTSYMBOL", "NSE", "2m", "2023-01-01", "2023-01-01")

    @patch('app.web.broker.broker.angel.api.data.get_br_symbol')
    @patch('app.web.broker.broker.angel.api.data.get_token')
    @patch('app.web.broker.broker.angel.api.data.get_api_response')
    def test_get_history_api_error(self, mock_get_api_response, mock_get_token, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "ANGEL_SYMBOL"
        mock_get_token.return_value = "ANGEL_TOKEN"
        mock_get_api_response.return_value = {
            "status": False,
            "message": "Historical data API error"
        }
        with self.assertRaisesRegex(Exception, "Error fetching historical data: Error from Angel API: Historical data API error"):
            self.broker_data.get_history("TESTSYMBOL", "NSE", "5m", "2023-01-01", "2023-01-01")

    @patch('app.web.broker.broker.angel.api.data.get_br_symbol')
    @patch('app.web.broker.broker.angel.api.data.get_token')
    @patch('app.web.broker.broker.angel.api.data.get_api_response')
    def test_get_history_empty_data(self, mock_get_api_response, mock_get_token, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "ANGEL_SYMBOL"
        mock_get_token.return_value = "ANGEL_TOKEN"
        mock_get_api_response.return_value = {
            "status": True,
            "data": []
        }
        with patch.object(self.broker_data, 'get_oi_history', return_value=pd.DataFrame(columns=['timestamp', 'oi'])):
            df = self.broker_data.get_history("TESTSYMBOL", "NSE", "5m", "2023-01-01", "2023-01-01")
            self.assertIsInstance(df, pd.DataFrame)
            self.assertTrue(df.empty)

    @patch('app.web.broker.broker.angel.api.data.get_br_symbol')
    @patch('app.web.broker.broker.angel.api.data.get_token')
    @patch('app.web.broker.broker.angel.api.data.get_api_response')
    def test_get_depth_success(self, mock_get_api_response, mock_get_token, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "ANGEL_SYMBOL"
        mock_get_token.return_value = "ANGEL_TOKEN"
        mock_get_api_response.return_value = {
            "status": True,
            "data": {
                "fetched": [
                    {
                        "depth": {
                            "buy": [{"price": 100.0, "quantity": 100}, {"price": 99.0, "quantity": 50}],
                            "sell": [{"price": 101.0, "quantity": 120}, {"price": 102.0, "quantity": 70}]
                        },
                        "high": 102.5,
                        "low": 98.5,
                        "ltp": 100.8,
                        "lastTradeQty": 20,
                        "open": 99.0,
                        "close": 99.8,
                        "tradeVolume": 5000,
                        "opnInterest": 600,
                        "totBuyQuan": 150,
                        "totSellQuan": 190
                    }
                ]
            }
        }

        depth = self.broker_data.get_depth("TESTSYMBOL", "NSE")

        self.assertIsInstance(depth, dict)
        self.assertEqual(len(depth['bids']), 5)
        self.assertEqual(depth['bids'][0]['price'], 100.0)
        self.assertEqual(depth['asks'][0]['price'], 101.0)
        self.assertEqual(depth['high'], 102.5)
        self.assertEqual(depth['low'], 98.5)
        self.assertEqual(depth['ltp'], 100.8)
        self.assertEqual(depth['totalbuyqty'], 150)
        self.assertEqual(depth['totalsellqty'], 190)
        mock_get_br_symbol.assert_called_once_with("TESTSYMBOL", "NSE")
        mock_get_token.assert_called_once_with("TESTSYMBOL", "NSE")
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.angel.api.data.get_br_symbol')
    @patch('app.web.broker.broker.angel.api.data.get_token')
    @patch('app.web.broker.broker.angel.api.data.get_api_response')
    def test_get_depth_api_error(self, mock_get_api_response, mock_get_token, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "ANGEL_SYMBOL"
        mock_get_token.return_value = "ANGEL_TOKEN"
        mock_get_api_response.return_value = {
            "status": False,
            "message": "Depth data API error"
        }

        with self.assertRaisesRegex(Exception, "Error from Angel API: Depth data API error"):
            self.broker_data.get_depth("TESTSYMBOL", "NSE")

    @patch('app.web.broker.broker.angel.api.data.get_br_symbol')
    @patch('app.web.broker.broker.angel.api.data.get_token')
    @patch('app.web.broker.broker.angel.api.data.get_api_response')
    def test_get_depth_no_data(self, mock_get_api_response, mock_get_token, mock_get_br_symbol):
        mock_get_br_symbol.return_value = "ANGEL_SYMBOL"
        mock_get_token.return_value = "ANGEL_TOKEN"
        mock_get_api_response.return_value = {
            "status": True,
            "data": {"fetched": []}
        }

        with self.assertRaisesRegex(Exception, "No depth data received"):
            self.broker_data.get_depth("TESTSYMBOL", "NSE")

    @patch('app.web.broker.broker.angel.api.data.get_br_symbol', side_effect=Exception("Symbol error"))
    def test_get_depth_exception(self, mock_get_br_symbol):
        with self.assertRaisesRegex(Exception, "Error fetching market depth: Symbol error"):
            self.broker_data.get_depth("TESTSYMBOL", "NSE")

    @patch('app.web.broker.broker.angel.api.order_api.get_api_response')
    def test_get_order_book_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "status": True,
            "data": [{"orderid": "123", "status": "open"}]
        }
        response = get_order_book(self.auth_token)
        self.assertTrue(response['status'])
        self.assertEqual(response['data'][0]['orderid'], '123')
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.angel.api.order_api.get_api_response')
    def test_get_trade_book_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "status": True,
            "data": [{"tradeid": "T1", "symbol": "TEST"}]
        }
        response = get_trade_book(self.auth_token)
        self.assertTrue(response['status'])
        self.assertEqual(response['data'][0]['tradeid'], 'T1')
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.angel.api.order_api.get_api_response')
    def test_get_positions_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "status": True,
            "data": [{"symbol": "TEST", "quantity": 10}]
        }
        response = get_positions(self.auth_token)
        self.assertTrue(response['status'])
        self.assertEqual(response['data'][0]['symbol'], 'TEST')
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.angel.api.order_api.get_api_response')
    def test_get_holdings_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "status": True,
            "data": [{"isin": "INE000A01025", "quantity": 5}]
        }
        response = get_holdings(self.auth_token)
        self.assertTrue(response['status'])
        self.assertEqual(response['data'][0]['isin'], 'INE000A01025')
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.angel.api.order_api.get_api_response')
    def test_place_order_api_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "status": True,
            "data": {"orderid": "ORD12345", "ordermsg": "Order placed successfully"}
        }
        response = place_order_api(self.auth_token, {"symbol": "TEST", "qty": 1})
        self.assertTrue(response['status'])
        self.assertEqual(response['data']['orderid'], 'ORD12345')
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.angel.api.order_api.get_api_response')
    def test_place_order_api_failure(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "status": False,
            "message": "Insufficient funds"
        }
        response = place_order_api(self.auth_token, {"symbol": "TEST", "qty": 1})
        self.assertFalse(response['status'])
        self.assertEqual(response['message'], 'Insufficient funds')
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.angel.api.order_api.get_api_response')
    def test_place_smartorder_api_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "status": True,
            "data": {"orderid": "SMARTORD67890", "ordermsg": "Smart order placed"}
        }
        response = place_smartorder_api(self.auth_token, {"symbol": "TEST", "qty": 1})
        self.assertTrue(response['status'])
        self.assertEqual(response['data']['orderid'], 'SMARTORD67890')
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.angel.api.order_api.get_api_response')
    def test_close_all_positions_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "status": True,
            "message": "All positions closed"
        }
        response = close_all_positions(self.auth_token)
        self.assertTrue(response['status'])
        self.assertEqual(response['message'], 'All positions closed')
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.angel.api.order_api.get_api_response')
    def test_cancel_order_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "status": True,
            "data": {"orderid": "ORD12345", "ordermsg": "Order cancelled"}
        }
        response = cancel_order(self.auth_token, "ORD12345", "TEST", "NSE")
        self.assertTrue(response['status'])
        self.assertEqual(response['data']['orderid'], 'ORD12345')
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.angel.api.order_api.get_api_response')
    def test_modify_order_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "status": True,
            "data": {"orderid": "ORD12345", "ordermsg": "Order modified"}
        }
        response = modify_order(self.auth_token, "ORD12345", {"qty": 2})
        self.assertTrue(response['status'])
        self.assertEqual(response['data']['orderid'], 'ORD12345')
        mock_get_api_response.assert_called_once()

    @patch('app.web.broker.broker.angel.api.order_api.get_api_response')
    def test_cancel_all_orders_api_success(self, mock_get_api_response):
        mock_get_api_response.return_value = {
            "status": True,
            "message": "All orders cancelled"
        }
        response = cancel_all_orders_api(self.auth_token, "TEST", "NSE")
        self.assertTrue(response['status'])
        self.assertEqual(response['message'], 'All orders cancelled')
        mock_get_api_response.assert_called_once()

if __name__ == '__main__':
    unittest.main()