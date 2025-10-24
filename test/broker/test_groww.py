import json
import re
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pandas as pd
import pytest
import pytz
from app.core.config import settings
from app.utils.httpx_client import get_httpx_client

# Import the API functions to be tested
from app.broker.broker.groww.api.auth_api import (
    authenticate_broker,
    generate_totp,
    get_access_token_via_totp,
)
from app.broker.broker.groww.api.data import BrokerData, get_api_response
from app.broker.broker.groww.api.funds import get_margin_data
from app.broker.broker.groww.api.order_api import (
    cancel_all_orders_api,
    cancel_order,
    close_all_positions,
    direct_get_order_book,
    direct_modify_order,
    direct_place_order_api,
    get_holdings,
    get_open_position,
    get_order_book,
    get_order_trades,
    get_positions,
    get_trade_book,
    modify_order,
    place_order_api,
    place_smartorder_api,
)

# Constants for testing
TEST_AUTH_TOKEN = "test_auth_token"
TEST_API_KEY = "test_api_key"
TEST_API_SECRET = "test_api_secret"
TEST_TOTP_CODE = "123456"
TEST_GROWW_ORDER_ID = "GROWW_ORDER_123"
TEST_OPENALGO_SYMBOL = "SBIN"
TEST_GROWW_SYMBOL = "SBIN"
TEST_EXCHANGE = "NSE"
TEST_SEGMENT_CASH = "CASH"
TEST_SEGMENT_FNO = "FNO"


@pytest.fixture
def mock_httpx_client():
    """Fixture to mock the httpx client."""
    with patch("app.utils.httpx_client.get_httpx_client") as mock_get_client:
        mock_client = MagicMock(spec=httpx.Client)
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_httpx_async_client():
    """Fixture to mock the httpx AsyncClient."""
    with patch("app.utils.httpx_client.get_httpx_client") as mock_get_client:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_settings():
    """Fixture to mock application settings."""
    with patch("app.core.config.settings") as mock_app_settings:
        mock_app_settings.BROKER_API_KEY = TEST_API_KEY
        mock_app_settings.BROKER_API_SECRET = TEST_API_SECRET
        yield mock_app_settings


@pytest.fixture
def mock_pyotp_totp():
    """Fixture to mock pyotp.TOTP."""
    with patch("app.web.broker.broker.groww.api.auth_api.pyotp.TOTP") as mock_totp_class:
        mock_totp_instance = MagicMock()
        mock_totp_instance.now.return_value = TEST_TOTP_CODE
        mock_totp_class.return_value = mock_totp_instance
        yield mock_totp_class


@pytest.fixture
def mock_get_br_symbol():
    """Fixture to mock get_br_symbol from token_db."""
    with patch("app.web.broker.broker.groww.api.data.get_br_symbol") as mock_br_symbol:
        mock_br_symbol.return_value = None  # Default to no conversion
        yield mock_br_symbol


@pytest.fixture
def mock_get_token():
    """Fixture to mock get_token from token_db."""
    with patch("app.web.broker.broker.groww.api.data.get_token") as mock_token:
        mock_token.return_value = "mock_token_123"
        yield mock_token


class TestGrowwAuth:
    """Tests for authentication functions in auth_api.py."""

    def test_generate_totp_success(self, mock_pyotp_totp):
        """Test successful TOTP generation."""
        api_secret = "JBSWY3DPEHPK3PXP"
        expected_totp = TEST_TOTP_CODE
        result = generate_totp(api_secret)
        mock_pyotp_totp.assert_called_once_with(api_secret)
        mock_pyotp_totp.return_value.now.assert_called_once()
        assert result == expected_totp

    def test_get_access_token_via_totp_success(self, mock_httpx_client, mock_pyotp_totp):
        """Test successful retrieval of access token via TOTP."""
        mock_httpx_client.post.return_value.status_code = 200
        mock_httpx_client.post.return_value.json.return_value = {"status": "SUCCESS", "token": TEST_AUTH_TOKEN}

        token, error = get_access_token_via_totp(TEST_API_KEY, TEST_API_SECRET)

        assert token == TEST_AUTH_TOKEN
        assert error is None
        mock_pyotp_totp.return_value.now.assert_called_once()
        mock_httpx_client.post.assert_called_once()
        args, kwargs = mock_httpx_client.post.call_args
        assert kwargs["url"] == "https://api.groww.in/v1/token/api/access"
        assert kwargs["headers"]["Authorization"] == f"Bearer {TEST_API_KEY}"
        assert kwargs["json"]["totp"] == TEST_TOTP_CODE

    def test_get_access_token_via_totp_api_error(self, mock_httpx_client, mock_pyotp_totp):
        """Test API error during access token retrieval."""
        mock_httpx_client.post.return_value.status_code = 400
        mock_httpx_client.post.return_value.json.return_value = {"status": "FAILED", "message": "Invalid credentials"}
        mock_httpx_client.post.return_value.text = json.dumps({"status": "FAILED", "message": "Invalid credentials"})

        token, error = get_access_token_via_totp(TEST_API_KEY, TEST_API_SECRET)

        assert token is None
        assert "HTTP error 400: " in error
        assert "Invalid credentials" in error
        mock_httpx_client.post.assert_called_once()

    def test_get_access_token_via_totp_exception(self, mock_httpx_client, mock_pyotp_totp):
        """Test exception during access token retrieval."""
        mock_httpx_client.post.side_effect = Exception("Network error")

        token, error = get_access_token_via_totp(TEST_API_KEY, TEST_API_SECRET)

        assert token is None
        assert "Request failed: Network error" in error
        mock_httpx_client.post.assert_called_once()

    def test_authenticate_broker_success(self, mock_settings, mock_httpx_client, mock_pyotp_totp):
        """Test successful broker authentication."""
        mock_httpx_client.post.return_value.status_code = 200
        mock_httpx_client.post.return_value.json.return_value = {"status": "SUCCESS", "token": TEST_AUTH_TOKEN}

        token, error = authenticate_broker(None)  # 'code' is not used in TOTP flow

        assert token == TEST_AUTH_TOKEN
        assert error is None
        mock_pyotp_totp.return_value.now.assert_called_once()
        mock_httpx_client.post.assert_called_once()

    def test_authenticate_broker_missing_credentials(self, mock_settings):
        """Test authentication with missing API key/secret."""
        mock_settings.BROKER_API_KEY = None
        mock_settings.BROKER_API_SECRET = None

        token, error = authenticate_broker(None)

        assert token is None
        assert "BROKER_API_KEY and BROKER_API_SECRET environment variables are required" in error

    def test_authenticate_broker_get_access_token_failure(self, mock_settings, mock_httpx_client, mock_pyotp_totp):
        """Test broker authentication when get_access_token_via_totp fails."""
        mock_httpx_client.post.return_value.status_code = 500
        mock_httpx_client.post.return_value.json.return_value = {"status": "FAILED", "message": "Internal error"}
        mock_httpx_client.post.return_value.text = json.dumps({"status": "FAILED", "message": "Internal error"})

        token, error = authenticate_broker(None)

        assert token is None
        assert "HTTP error 500" in error
        mock_httpx_client.post.assert_called_once()

    def test_authenticate_broker_exception(self, mock_settings):
        """Test unexpected exception during broker authentication."""
        # Simulate an error in accessing settings
        del mock_settings.BROKER_API_KEY
        token, error = authenticate_broker(None)
        assert token is None
        assert "An exception occurred" in error


class TestGrowwData:
    """Tests for data retrieval functions in data.py."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_httpx_client, mock_get_br_symbol, mock_get_token):
        self.mock_httpx_client = mock_httpx_client
        self.mock_get_br_symbol = mock_get_br_symbol
        self.mock_get_token = mock_get_token
        self.broker_data = BrokerData(TEST_AUTH_TOKEN)

    @pytest.mark.parametrize(
        "openalgo_symbol, openalgo_exchange, expected_groww_symbol",
        [
            ("SBIN30SEP25FUT", "NFO", "SBIN25SEPFUT"),
            ("SBIN30SEP25800CE", "NFO", "SBIN25SEP800CE"),
            ("NIFTY30OCT2519500PE", "NFO", "NIFTY25OCT19500PE"),
            ("RELIANCE", "NSE", "RELIANCE"),  # Equity symbol, no change
        ],
    )
    def test_convert_openalgo_to_groww_derivative_symbol(
        self, openalgo_symbol, openalgo_exchange, expected_groww_symbol
    ):
        """Test conversion of OpenAlgo derivative symbols to Groww format."""
        # This function is internal and does not use get_br_symbol or get_token
        result = self.broker_data._convert_openalgo_to_groww_derivative_symbol(openalgo_symbol)
        assert result == expected_groww_symbol

    @pytest.mark.parametrize(
        "symbol, exchange, expected_groww_exchange, expected_segment, expected_trading_symbol, mock_br_symbol_val",
        [
            ("RELIANCE", "NSE", "NSE", "CASH", "RELIANCE", None),
            ("RELIANCE", "BSE", "BSE", "CASH", "RELIANCE", "RIL_BSE"),
            ("NIFTY25OCTFUT", "NFO", "NSE", "FNO", "NIFTY25OCTFUT", "NIFTY25OCTFUT_GROWW"),
            ("NIFTY25OCT19500CE", "NFO", "NSE", "FNO", "NIFTY25OCT19500CE", None),
            ("BANKNIFTY", None, "NSE", "CASH", "BANKNIFTY", None),  # Default exchange
        ],
    )
    def test_convert_to_groww_params(
        self,
        symbol,
        exchange,
        expected_groww_exchange,
        expected_segment,
        expected_trading_symbol,
        mock_br_symbol_val,
        mock_get_br_symbol,
    ):
        """Test conversion of OpenAlgo parameters to Groww API parameters."""
        mock_get_br_symbol.return_value = mock_br_symbol_val
        groww_exchange, segment, trading_symbol = self.broker_data._convert_to_groww_params(symbol, exchange)

        assert groww_exchange == expected_groww_exchange
        assert segment == expected_segment
        assert trading_symbol == expected_trading_symbol
        if mock_br_symbol_val:
            mock_get_br_symbol.assert_called_with(symbol, exchange)
        if exchange in ["NFO", "BFO"] and not mock_br_symbol_val:
            # Ensure derivative symbol conversion is attempted if not in DB
            pass # Implicitly checked by expected_trading_symbol if not None

    def test_convert_to_groww_params_unsupported_exchange(self):
        """Test _convert_to_groww_params with an unsupported exchange."""
        with pytest.raises(ValueError, match="Unsupported exchange: XYZ"):
            self.broker_data._convert_to_groww_params("SYMBOL", "XYZ")

    @pytest.mark.parametrize(
        "interval, initial_df, expected_timestamps",
        [
            (
                "D",
                pd.DataFrame(
                    [
                        {"timestamp": "2023-01-01", "open": 100, "high": 105, "low": 98, "close": 103, "volume": 1000},
                        {"timestamp": "2023-01-02", "open": 103, "high": 108, "low": 101, "close": 106, "volume": 1200},
                    ]
                ).set_index("timestamp"),
                [
                    pytz.timezone("Asia/Kolkata").localize(datetime(2023, 1, 1, 9, 15)),
                    pytz.timezone("Asia/Kolkata").localize(datetime(2023, 1, 2, 9, 15)),
                ],
            ),
            (
                "1m",
                pd.DataFrame(
                    [
                        {"timestamp": "2023-01-01 09:14:00", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 100},
                        {"timestamp": "2023-01-01 09:15:00", "open": 100, "high": 102, "low": 99, "close": 101, "volume": 150},
                        {"timestamp": "2023-01-01 15:31:00", "open": 105, "high": 106, "low": 104, "close": 105, "volume": 200},
                    ]
                ).set_index("timestamp"),
                [
                    pytz.timezone("Asia/Kolkata").localize(datetime(2023, 1, 1, 9, 15)),
                    pytz.timezone("Asia/Kolkata").localize(datetime(2023, 1, 1, 9, 15)),
                    pytz.timezone("Asia/Kolkata").localize(datetime(2023, 1, 1, 15, 30)),
                ],
            ),
        ],
    )
    def test_fix_timestamps(self, interval, initial_df, expected_timestamps):
        """Test fixing timestamps for daily/weekly and intraday data."""
        result_df = self.broker_data.fix_timestamps(initial_df.copy(), interval)

        assert not result_df.empty
        # For daily/weekly, all timestamps should be 09:15:00 IST for that day
        if interval == "D":
            assert all(dt.time() == datetime(2000, 1, 1, 9, 15).time() for dt in result_df.index)
            assert len(result_df) == len(expected_timestamps)
        # For intraday, timestamps outside market hours should be clamped
        elif interval == "1m":
            assert len(result_df) == len(initial_df)
            assert result_df.index[0] == expected_timestamps[0]
            assert result_df.index[1] == expected_timestamps[1]
            assert result_df.index[2] == expected_timestamps[2]
            assert all(dt.time() >= datetime(2000, 1, 1, 9, 15).time() for dt in result_df.index)
            assert all(dt.time() <= datetime(2000, 1, 1, 15, 30).time() for dt in result_df.index)

    def test_fix_timestamps_empty_df(self):
        """Test fix_timestamps with an empty DataFrame."""
        empty_df = pd.DataFrame()
        result = self.broker_data.fix_timestamps(empty_df, "1m")
        assert result.empty

    @pytest.mark.parametrize(
        "api_response, expected_df_shape, expected_columns",
        [
            # Success case with list of candles
            (
                {
                    "status": "SUCCESS",
                    "payload": {
                        "candles": [
                            [1672502400000, 100, 105, 98, 103, 1000],
                            [1672588800000, 103, 108, 101, 106, 1200],
                        ]
                    },
                },
                (2, 7),  # 2 rows, 7 columns (timestamp, open, high, low, close, volume, oi)
                ["timestamp", "open", "high", "low", "close", "volume", "oi"],
            ),
            # Success case with dict of candles
            (
                {
                    "status": "SUCCESS",
                    "payload": {
                        "candles": [
                            {
                                "timestamp": 1672502400000,
                                "open": 100,
                                "high": 105,
                                "low": 98,
                                "close": 103,
                                "volume": 1000,
                            },
                            {
                                "timestamp": 1672588800000,
                                "open": 103,
                                "high": 108,
                                "low": 101,
                                "close": 106,
                                "volume": 1200,
                            },
                        ]
                    },
                },
                (2, 7),
                ["timestamp", "open", "high", "low", "close", "volume", "oi"],
            ),
            # Empty candles list
            ({"status": "SUCCESS", "payload": {"candles": []}}, (0, 7), []),
            # API error response
            ({"status": "FAILED", "message": "API error"}, (0, 7), []),
            # No payload
            ({"status": "SUCCESS"}, (0, 7), []),
        ],
    )
    @patch("app.web.broker.broker.groww.api.data.get_api_response")
    def test_get_history(
        self,
        mock_get_api_response,
        api_response,
        expected_df_shape,
        expected_columns,
        mock_get_br_symbol,
    ):
        """Test get_history for various API responses and timeframes."""
        mock_get_api_response.return_value = api_response
        mock_get_br_symbol.return_value = None  # No symbol mapping for simplicity

        start_time = "2023-01-01"
        end_time = "2023-01-02"
        timeframe = "D"

        df = self.broker_data.get_history(TEST_OPENALGO_SYMBOL, TEST_EXCHANGE, timeframe, start_time, end_time)

        if expected_df_shape[0] > 0:
            assert df.shape == expected_df_shape
            assert list(df.columns) == expected_columns
            # Assert timestamps are UTC localized
            assert all(
                isinstance(ts, (int, float)) for ts in df["timestamp"]
            )  # Unix timestamp
        else:
            assert df.empty
            if expected_columns:
                assert list(df.columns) == expected_columns

        # Ensure get_api_response was called
        mock_get_api_response.assert_called_once()
        args, kwargs = mock_get_api_response.call_args
        assert kwargs["endpoint"] == "/v1/historical/candle/range"
        assert kwargs["params"]["trading_symbol"] == TEST_OPENALGO_SYMBOL
        assert kwargs["params"]["interval_in_minutes"] == self.broker_data.timeframe_map[timeframe]

    @patch("app.web.broker.broker.groww.api.data.get_api_response")
    def test_get_history_chunking(self, mock_get_api_response, mock_get_br_symbol):
        """Test get_history with date range requiring chunking."""
        mock_get_br_symbol.return_value = None

        # Simulate two chunks of data
        mock_get_api_response.side_effect = [
            {
                "status": "SUCCESS",
                "payload": {
                    "candles": [
                        [1672502400000, 100, 105, 98, 103, 1000],  # 2023-01-01
                    ]
                },
            },
            {
                "status": "SUCCESS",
                "payload": {
                    "candles": [
                        [1672588800000, 103, 108, 101, 106, 1200],  # 2023-01-02
                    ]
                },
            },
            {
                "status": "SUCCESS",
                "payload": {
                    "candles": [
                        [1672675200000, 106, 110, 104, 109, 1500],  # 2023-01-03
                    ]
                },
            },
        ]

        start_time = "2023-01-01"
        end_time = "2023-01-03"
        timeframe = "1m"  # Should use chunk_size = 3

        df = self.broker_data.get_history(TEST_OPENALGO_SYMBOL, TEST_EXCHANGE, timeframe, start_time, end_time)

        assert not df.empty
        assert len(df) == 3
        assert mock_get_api_response.call_count == 3  # Three chunks for 3 days

    @patch("app.web.broker.broker.groww.api.data.get_api_response")
    def test_get_history_weekly_resampling(self, mock_get_api_response, mock_get_br_symbol):
        """Test get_history with weekly timeframe and resampling."""
        mock_get_br_symbol.return_value = None

        # Simulate daily data for a period that results in weekly candles
        mock_get_api_response.return_value = {
            "status": "SUCCESS",
            "payload": {
                "candles": [
                    [1672502400000, 100, 105, 98, 103, 1000],  # Mon 2023-01-01 (adjusted to actual Monday)
                    [1672588800000, 103, 108, 101, 106, 1200],  # Tue 2023-01-02
                    [1672675200000, 106, 110, 104, 109, 1500],  # Wed 2023-01-03
                    [1672761600000, 109, 112, 107, 111, 1300],  # Thu 2023-01-04
                    [1672848000000, 111, 115, 109, 114, 1600],  # Fri 2023-01-05
                    [1673193600000, 114, 118, 112, 116, 1700],  # Mon 2023-01-08 (next week)
                    [1673280000000, 116, 120, 114, 119, 1800],  # Tue 2023-01-09
                ]
            },
        }

        start_time = "2023-01-01"  # Sunday
        end_time = "2023-01-09"  # Tuesday
        timeframe = "W"

        df = self.broker_data.get_history(TEST_OPENALGO_SYMBOL, TEST_EXCHANGE, timeframe, start_time, end_time)

        assert not df.empty
        assert len(df) == 2  # Should result in two weekly candles
        assert df["open"].iloc[0] == 100  # Open of first week
        assert df["close"].iloc[0] == 114  # Close of first week (Fri)
        assert df["volume"].iloc[0] == 6600  # Sum of volume for first week
        assert df["open"].iloc[1] == 114  # Open of second week
        assert df["close"].iloc[1] == 119  # Close of second week (Tue)

    def test_get_intervals(self):
        """Test get_intervals returns the correct supported timeframes."""
        intervals = self.broker_data.get_intervals()
        assert intervals["status"] == "success"
        assert "minutes" in intervals["data"]
        assert "1m" in intervals["data"]["minutes"]
        assert "D" in intervals["data"]["days"]
        assert "W" in intervals["data"]["weeks"]

    @pytest.mark.parametrize(
        "start_time, end_time, requested_interval, expected_interval_minutes",
        [
            ("2023-01-01", "2023-01-02", "1m", "1"),  # 2 days, 1m requested, 1m allowed
            ("2023-01-01", "2023-01-05", "1m", "1"),  # 5 days, 1m requested, 5m min, should return 1m
            ("2023-01-01", "2023-01-05", "5m", "5"),  # 5 days, 5m requested, 5m allowed
            ("2023-01-01", "2023-01-16", "1m", "10"),  # 16 days, 1m requested, 10m min, should return 10m
            ("2023-01-01", "2023-03-01", "1m", "60"),  # ~60 days, 1m requested, 60m min, should return 60m
            ("2023-01-01", "2024-01-01", "1h", "240"),  # ~365 days, 1h requested, 240m min, should return 240m
            ("2023-01-01", "2026-01-01", "4h", "1440"),  # >1080 days, 4h requested, 1440m min, should return 1440m
            ("2023-01-01", "2026-01-01", "D", "1440"),  # >1080 days, D requested, 1440m min, should return 1440m
            ("2023-01-01", "2026-01-01", "W", "10080"), # >1080 days, W requested, 10080m min, should return 10080m
            ("2023-01-01", "2023-01-01", "1d", "1440"), # Map 1d to D, then to 1440
            ("2023-01-01", "2023-01-01", "1w", "10080"), # Map 1w to W, then to 10080
        ],
    )
    def test_get_valid_interval(
        self, start_time, end_time, requested_interval, expected_interval_minutes
    ):
        """Test get_valid_interval based on Groww's time-based constraints."""
        result = self.broker_data.get_valid_interval(start_time, end_time, requested_interval)
        assert result == expected_interval_minutes

    @patch("app.web.broker.broker.groww.api.data.get_api_response")
    def test_get_quotes_single_symbol_success(self, mock_get_api_response, mock_get_br_symbol, mock_get_token):
        """Test successful retrieval of quotes for a single symbol."""
        mock_get_api_response.return_value = {
            "status": "SUCCESS",
            "payload": {
                "last_price": 150.50,
                "ohlc": {"open": 149.50, "high": 150.50, "low": 148.50, "close": 149.50},
                "volume": 100000,
                "day_change": 1.00,
                "day_change_perc": 0.67,
                "bid_price": 150.45,
                "bid_quantity": 500,
                "offer_price": 150.55,
                "offer_quantity": 700,
                "total_buy_quantity": 10000,
                "total_sell_quantity": 12000,
                "last_trade_time": int(datetime.now().timestamp() * 1000),
                "upper_circuit_limit": 160.0,
                "lower_circuit_limit": 140.0,
                "open_interest": 0,
            },
        }
        mock_get_br_symbol.return_value = None
        mock_get_token.return_value = "mock_token_123"

        symbol_list = {"symbol": TEST_OPENALGO_SYMBOL, "exchange": TEST_EXCHANGE}
        result = self.broker_data.get_quotes(symbol_list)

        assert result["ltp"] == 150.50
        assert result["open"] == 149.50
        assert result["high"] == 150.50
        assert result["low"] == 148.50
        assert result["prev_close"] == 149.50
        assert result["volume"] == 100000
        assert result["bid"] == 150.45
        assert result["ask"] == 150.55
        assert result["oi"] == 0  # Equity, so OI should be 0

        mock_get_api_response.assert_called_once()
        args, kwargs = mock_get_api_response.call_args
        assert kwargs["endpoint"] == "/v1/live-data/quote"
        assert kwargs["params"]["trading_symbol"] == TEST_OPENALGO_SYMBOL
        assert kwargs["params"]["exchange"] == TEST_EXCHANGE
        assert kwargs["params"]["segment"] == TEST_SEGMENT_CASH

    @patch("app.web.broker.broker.groww.api.data.get_api_response")
    def test_get_quotes_multiple_symbols_success(self, mock_get_api_response, mock_get_br_symbol, mock_get_token):
        """Test successful retrieval of quotes for multiple symbols."""
        mock_get_api_response.side_effect = [
            {
                "status": "SUCCESS",
                "payload": {
                    "last_price": 150.50,
                    "ohlc": {"open": 149.50, "high": 150.50, "low": 148.50, "close": 149.50},
                    "volume": 100000,
                    "day_change": 1.00,
                    "day_change_perc": 0.67,
                    "bid_price": 150.45,
                    "bid_quantity": 500,
                    "offer_price": 150.55,
                    "offer_quantity": 700,
                    "total_buy_quantity": 10000,
                    "total_sell_quantity": 12000,
                    "last_trade_time": int(datetime.now().timestamp() * 1000),
                    "upper_circuit_limit": 160.0,
                    "lower_circuit_limit": 140.0,
                    "open_interest": 0,
                },
            },
            {
                "status": "SUCCESS",
                "payload": {
                    "last_price": 200.00,
                    "ohlc": {"open": 199.00, "high": 201.00, "low": 198.00, "close": 199.50},
                    "volume": 50000,
                    "day_change": 0.50,
                    "day_change_perc": 0.25,
                    "bid_price": 199.90,
                    "bid_quantity": 300,
                    "offer_price": 200.10,
                    "offer_quantity": 400,
                    "total_buy_quantity": 5000,
                    "total_sell_quantity": 6000,
                    "last_trade_time": int(datetime.now().timestamp() * 1000),
                    "upper_circuit_limit": 210.0,
                    "lower_circuit_limit": 190.0,
                    "open_interest": 0,
                },
            },
        ]
        mock_get_br_symbol.return_value = None
        mock_get_token.return_value = "mock_token_123"

        symbol_list = [
            {"symbol": "SBIN", "exchange": "NSE"},
            {"symbol": "TCS", "exchange": "NSE"},
        ]
        result = self.broker_data.get_quotes(symbol_list)

        assert result["status"] == "success"
        assert len(result["data"]) == 2
        assert result["data"][0]["ltp"] == 150.50
        assert result["data"][1]["ltp"] == 200.00
        assert mock_get_api_response.call_count == 2

    @patch("app.web.broker.broker.groww.api.data.get_api_response")
    def test_get_quotes_api_error(self, mock_get_api_response, mock_get_br_symbol, mock_get_token):
        """Test get_quotes with an API error response."""
        mock_get_api_response.return_value = {"error": "API rate limit exceeded"}
        mock_get_br_symbol.return_value = None
        mock_get_token.return_value = "mock_token_123"

        symbol_list = "RELIANCE"
        result = self.broker_data.get_quotes(symbol_list)

        assert result["ltp"] == 0
        assert "API rate limit exceeded" in result["error"]

    @patch("app.web.broker.broker.groww.api.data.get_api_response")
    def test_get_quotes_derivative_oi(self, mock_get_api_response, mock_get_br_symbol, mock_get_token):
        """Test get_quotes for a derivative symbol with Open Interest."""
        mock_get_api_response.return_value = {
            "status": "SUCCESS",
            "payload": {
                "last_price": 100.0,
                "ohlc": {"open": 99.0, "high": 101.0, "low": 98.0, "close": 99.5},
                "volume": 1000,
                "day_change": 1.0,
                "day_change_perc": 1.0,
                "bid_price": 99.9,
                "bid_quantity": 100,
                "offer_price": 100.1,
                "offer_quantity": 150,
                "total_buy_quantity": 500,
                "total_sell_quantity": 600,
                "last_trade_time": int(datetime.now().timestamp() * 1000),
                "upper_circuit_limit": 105.0,
                "lower_circuit_limit": 95.0,
                "open_interest": 5000,  # OI for derivative
            },
        }
        mock_get_br_symbol.return_value = None
        mock_get_token.return_value = "mock_token_123"

        symbol_list = {"symbol": "NIFTY25OCT19500CE", "exchange": "NFO"}
        result = self.broker_data.get_quotes(symbol_list)

        assert result["ltp"] == 100.0
        assert result["oi"] == 5000  # OI should be present for derivative

    @patch("app.web.broker.broker.groww.api.data.get_api_response")
    def test_get_depth_success(self, mock_get_api_response, mock_get_br_symbol, mock_get_token):
        """Test successful retrieval of market depth."""
        mock_get_api_response.return_value = {
            "status": "SUCCESS",
            "payload": {
                "last_price": 150.50,
                "last_trade_quantity": 50,
                "ohlc": {"open": 149.50, "high": 150.50, "low": 148.50, "close": 149.50},
                "volume": 100000,
                "total_buy_quantity": 10000,
                "total_sell_quantity": 12000,
                "open_interest": 0,
                "depth": {
                    "buy": [
                        {"price": 150.45, "quantity": 500},
                        {"price": 150.40, "quantity": 300},
                    ],
                    "sell": [
                        {"price": 150.55, "quantity": 700},
                        {"price": 150.60, "quantity": 400},
                    ],
                },
            },
        }
        mock_get_br_symbol.return_value = None
        mock_get_token.return_value = "mock_token_123"

        symbol_list = {"symbol": TEST_OPENALGO_SYMBOL, "exchange": TEST_EXCHANGE}
        result = self.broker_data.get_depth(symbol_list)

        assert result["ltp"] == 150.50
        assert result["ltq"] == 50
        assert len(result["bids"]) == 5
        assert result["bids"][0]["price"] == 150.45
        assert result["bids"][0]["quantity"] == 500
        assert len(result["asks"]) == 5
        assert result["asks"][0]["price"] == 150.55
        assert result["asks"][0]["quantity"] == 700
        assert result["open"] == 149.50
        assert result["high"] == 150.50
        assert result["low"] == 148.50
        assert result["prev_close"] == 149.50
        assert result["volume"] == 100000
        assert result["totalbuyqty"] == 10000
        assert result["totalsellqty"] == 12000
        assert result["oi"] == 0

        mock_get_api_response.assert_called_once()
        args, kwargs = mock_get_api_response.call_args
        assert kwargs["endpoint"] == "/v1/live-data/quote"
        assert kwargs["params"]["trading_symbol"] == TEST_OPENALGO_SYMBOL
        assert kwargs["params"]["exchange"] == TEST_EXCHANGE
        assert kwargs["params"]["segment"] == TEST_SEGMENT_CASH

    @patch("app.web.broker.broker.groww.api.data.get_api_response")
    def test_get_depth_no_depth_data(self, mock_get_api_response, mock_get_br_symbol, mock_get_token):
        """Test get_depth when API response has no depth data."""
        mock_get_api_response.return_value = {
            "status": "SUCCESS",
            "payload": {
                "last_price": 150.50,
                "last_trade_quantity": 50,
                "ohlc": {"open": 149.50, "high": 150.50, "low": 148.50, "close": 149.50},
                "volume": 100000,
                "total_buy_quantity": 10000,
                "total_sell_quantity": 12000,
                "open_interest": 0,
                "depth": None,  # No depth data
            },
        }
        mock_get_br_symbol.return_value = None
        mock_get_token.return_value = "mock_token_123"

        symbol_list = {"symbol": TEST_OPENALGO_SYMBOL, "exchange": TEST_EXCHANGE}
        result = self.broker_data.get_depth(symbol_list)

        assert result["ltp"] == 150.50
        assert len(result["bids"]) == 5
        assert all(bid["price"] == 0 for bid in result["bids"])
        assert len(result["asks"]) == 5
        assert all(ask["price"] == 0 for ask in result["asks"])

    @patch("app.web.broker.broker.groww.api.data.get_api_response")
    def test_get_depth_api_error(self, mock_get_api_response, mock_get_br_symbol, mock_get_token):
        """Test get_depth with an API error response."""
        mock_get_api_response.return_value = {"error": "API error"}
        mock_get_br_symbol.return_value = None
        mock_get_token.return_value = "mock_token_123"

        symbol_list = "RELIANCE"
        result = self.broker_data.get_depth(symbol_list)

        assert result == {}  # Should return empty dict on API error

    def test_get_market_depth_alias(self):
        """Test get_market_depth is an alias for get_depth."""
        # Directly call get_market_depth and verify it calls get_depth
        with patch.object(self.broker_data, "get_depth") as mock_get_depth:
            mock_get_depth.return_value = {"mock_depth_data": True}
            result = self.broker_data.get_market_depth("SYMBOL")
            mock_get_depth.assert_called_once_with("SYMBOL", timeout=5)
            assert result == {"mock_depth_data": True}


class TestGrowwFunds:
    """Tests for funds-related functions in funds.py."""

    @patch("app.web.broker.broker.groww.api.funds.get_httpx_client")
    def test_get_margin_data_success(self, mock_get_client):
        """Test successful retrieval of margin data."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {
            "status": "SUCCESS",
            "payload": {
                "clear_cash": 10000.50,
                "collateral_available": 5000.25,
                "net_margin_used": 2000.75,
                "brokerage_and_charges": 10.00,
                "adhoc_margin": 500.00,
                "equity_margin_details": {
                    "cnc_balance_available": 8000.00,
                    "mis_balance_available": 2000.00,
                },
                "fno_margin_details": {
                    "future_balance_available": 3000.00,
                    "option_buy_balance_available": 1000.00,
                    "option_sell_balance_available": 2000.00,
                },
            },
        }

        result = get_margin_data(TEST_AUTH_TOKEN)

        assert result["availablecash"] == "10000.50"
        assert result["collateral"] == "5000.25"
        assert result["utiliseddebits"] == "2000.75"
        assert result["brokerage_and_charges"] == "10.00"
        assert result["adhoc_margin"] == "500.00"
        assert result["equity_cnc_balance"] == "8000.00"
        assert result["equity_mis_balance"] == "2000.00"
        assert result["fno_futures_balance"] == "3000.00"
        assert result["fno_option_buy_balance"] == "1000.00"
        assert result["fno_option_sell_balance"] == "2000.00"
        assert result["m2munrealized"] == "0.00"  # Default to 0 as not implemented
        assert result["m2mrealized"] == "0.00"  # Default to 0 as not implemented

        mock_client.get.assert_called_once_with(
            "https://api.groww.in/v1/margins/detail/user",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {TEST_AUTH_TOKEN}",
            },
        )

    @patch("app.web.broker.broker.groww.api.funds.get_httpx_client")
    def test_get_margin_data_api_error(self, mock_get_client):
        """Test get_margin_data with an API error."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.return_value.status_code = 401
        mock_client.get.return_value.text = "Unauthorized"

        result = get_margin_data(TEST_AUTH_TOKEN)
        assert result == {}
        mock_client.get.assert_called_once()

    @patch("app.web.broker.broker.groww.api.funds.get_httpx_client")
    def test_get_margin_data_empty_payload(self, mock_get_client):
        """Test get_margin_data when API returns empty payload."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {"status": "SUCCESS", "payload": {}}

        result = get_margin_data(TEST_AUTH_TOKEN)
        assert result == {}
        mock_client.get.assert_called_once()

    @patch("app.web.broker.broker.groww.api.funds.get_httpx_client")
    def test_get_margin_data_exception(self, mock_get_client):
        """Test get_margin_data with an unexpected exception."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.side_effect = Exception("Network unreachable")

        result = get_margin_data(TEST_AUTH_TOKEN)
        assert result == {}
        mock_client.get.assert_called_once()


class TestGrowwOrder:
    """Tests for order-related functions in order_api.py."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_httpx_client):
        self.mock_httpx_client = mock_httpx_client

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    @patch("app.web.broker.broker.groww.api.order_api.SEGMENT_CASH", "CASH")
    @patch("app.web.broker.broker.groww.api.order_api.SEGMENT_FNO", "FNO")
    def test_direct_get_order_book_success(self, mock_get_client):
        """Test successful retrieval of order book."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.side_effect = [
            # First call for CASH segment, page 0
            MagicMock(
                status_code=200,
                json=lambda: {
                    "status": "SUCCESS",
                    "payload": {
                        "order_list": [
                            {
                                "groww_order_id": "CASH_ORDER_1",
                                "trading_symbol": "RELIANCE",
                                "exchange": "NSE",
                                "segment": "CASH",
                                "order_status": "FILLED",
                                "filled_quantity": 10,
                                "transaction_type": "BUY",
                                "product": "CNC",
                            }
                        ]
                    },
                },
            ),
            # Second call for FNO segment, page 0
            MagicMock(
                status_code=200,
                json=lambda: {
                    "status": "SUCCESS",
                    "payload": {
                        "order_list": [
                            {
                                "groww_order_id": "GLTFO_ORDER_1",
                                "trading_symbol": "NIFTY25OCTFUT",
                                "exchange": "NSE",
                                "segment": "FNO",
                                "order_status": "PENDING",
                                "filled_quantity": 0,
                                "transaction_type": "SELL",
                                "product": "MIS",
                            }
                        ]
                    },
                },
            ),
        ]

        # Mock db_session and SymToken for symbol conversion
        with patch("app.web.broker.broker.groww.api.order_api.db_session") as mock_db_session, \
             patch("app.web.broker.broker.groww.api.order_api.SymToken") as mock_symtoken, \
             patch("app.web.broker.broker.groww.api.order_api.get_oa_symbol") as mock_get_oa_symbol:

            mock_db_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None
            mock_get_oa_symbol.side_effect = [
                None,  # First call for NIFTY25OCTFUT, no token conversion
                "NIFTY25OCTFUT_OPENALGO"  # Second call for NIFTY25OCTFUT, successful pattern conversion
            ]

            result = direct_get_order_book(TEST_AUTH_TOKEN)

            assert result["raw_response"]["status"] == "SUCCESS"
            assert len(result["data"]) == 2
            assert result["data"][0]["groww_order_id"] == "CASH_ORDER_1"
            assert result["data"][0]["symbol"] == "RELIANCE"
            assert result["data"][0]["exchange"] == "NSE"  # Equity exchange remains NSE
            assert result["data"][1]["groww_order_id"] == "GLTFO_ORDER_1"
            assert result["data"][1]["symbol"] == "NIFTY25OCTFUT"
            assert result["data"][1]["exchange"] == "NFO"  # FNO exchange is remapped to NFO

            assert mock_client.get.call_count == 2  # One for CASH, one for FNO

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    def test_direct_get_order_book_api_error(self, mock_get_client):
        """Test direct_get_order_book with an API error."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "Server error", request=httpx.Request("GET", "http://test.com"), response=httpx.Response(500)
        )

        result = direct_get_order_book(TEST_AUTH_TOKEN)
        assert result["raw_response"]["status"] == "FAILURE"
        assert result["data"] == []

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    def test_direct_get_order_book_empty_response(self, mock_get_client):
        """Test direct_get_order_book with empty response from API."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {
            "status": "SUCCESS",
            "payload": {"order_list": []},
        }

        result = direct_get_order_book(TEST_AUTH_TOKEN)
        assert result["raw_response"]["status"] == "SUCCESS"
        assert result["data"] == []

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    def test_get_trade_book_success(self, mock_get_client):
        """Test successful retrieval of trade book."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock order book response (containing executed orders)
        with patch("app.web.broker.broker.groww.api.order_api.get_order_book") as mock_get_order_book:
            mock_get_order_book.return_value = (
                {
                    "data": [
                        {
                            "groww_order_id": "CASH_ORDER_1",
                            "trading_symbol": "RELIANCE",
                            "exchange": "NSE",
                            "segment": "CASH",
                            "order_status": "FILLED",
                            "filled_quantity": 10,
                            "transaction_type": "BUY",
                            "product": "CNC",
                            "price": 250000,  # In paise
                        },
                        {
                            "groww_order_id": "GLTFO_ORDER_1",
                            "trading_symbol": "NIFTY25OCTFUT",
                            "exchange": "NSE",
                            "segment": "FNO",
                            "order_status": "EXECUTED",
                            "filled_quantity": 5,
                            "transaction_type": "SELL",
                            "product": "MIS",
                            "price": 1950000,  # In paise
                        },
                    ]
                },
                200,
            )

            # Mock get_order_trades for CASH order
            with patch("app.web.broker.broker.groww.api.order_api.get_order_trades") as mock_get_order_trades:
                mock_get_order_trades.side_effect = [
                    (
                        {
                            "status": "success",
                            "trades": [
                                {
                                    "groww_trade_id": "TRADE_1",
                                    "groww_order_id": "CASH_ORDER_1",
                                    "trading_symbol": "RELIANCE",
                                    "quantity": 10,
                                    "price": 250000,  # In paise
                                    "trade_date_time": "2023-01-01T10:00:00",
                                    "transaction_type": "BUY",
                                    "product": "CNC",
                                    "exchange": "NSE",
                                    "segment": "CASH",
                                }
                            ],
                        },
                        200,
                    ),
                    # Mock for FNO order returning 404, triggering synthetic trade
                    (
                        {"status": "error", "message": "Trades not found"},
                        404,
                    ),
                ]

                result, status_code = get_trade_book(TEST_AUTH_TOKEN)

                assert status_code == 200
                assert result["status"] == "success"
                assert len(result["data"]) == 2  # One real, one synthetic
                assert result["data"][0]["tradingSymbol"] == "RELIANCE"
                assert result["data"][0]["tradedPrice"] == 2500.00  # Converted from paise
                assert result["data"][1]["tradingSymbol"] == "NIFTY25OCTFUT"
                assert result["data"][1]["tradedPrice"] == 19500.00  # Converted from paise

                mock_get_order_book.assert_called_once_with(TEST_AUTH_TOKEN)
                assert mock_get_order_trades.call_count == 2

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    def test_get_trade_book_no_orders(self, mock_get_client):
        """Test get_trade_book when no orders are found."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        with patch("app.web.broker.broker.groww.api.order_api.get_order_book") as mock_get_order_book:
            mock_get_order_book.return_value = ({"data": []}, 200)  # Empty order book

            result, status_code = get_trade_book(TEST_AUTH_TOKEN)

            assert status_code == 200
            assert result["status"] == "success"
            assert result["message"] == "No orders found"
            assert result["data"] == []
            mock_get_order_book.assert_called_once_with(TEST_AUTH_TOKEN)

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    def test_get_trade_book_order_book_api_error(self, mock_get_client):
        """Test get_trade_book when get_order_book returns an API error."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        with patch("app.web.broker.broker.groww.api.order_api.get_order_book") as mock_get_order_book:
            mock_get_order_book.return_value = ({"status": "error", "message": "Order book error"}, 500)

            result, status_code = get_trade_book(TEST_AUTH_TOKEN)

            assert status_code == 500
            assert result["status"] == "error"
            assert "Order book error" in result["message"]
            assert result["data"] == []
            mock_get_order_book.assert_called_once_with(TEST_AUTH_TOKEN)

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    @patch("app.web.broker.broker.groww.api.order_api.get_oa_symbol")
    def test_get_positions_success(self, mock_get_oa_symbol, mock_get_client):
        """Test successful retrieval of positions."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.side_effect = [
            # CASH segment response
            MagicMock(
                status_code=200,
                json=lambda: {
                    "status": "SUCCESS",
                    "payload": {
                        "positions": [
                            {
                                "trading_symbol": "RELIANCE",
                                "exchange": "NSE",
                                "segment": "CASH",
                                "quantity": 10,
                                "net_price": 250000,  # In paise
                                "credit_quantity": 10,
                                "debit_quantity": 0,
                                "credit_price": 250000,
                                "product": "CNC",
                                "symbol_isin": "INE002A01018",
                            }
                        ]
                    },
                },
            ),
            # FNO segment response
            MagicMock(
                status_code=200,
                json=lambda: {
                    "status": "SUCCESS",
                    "payload": {
                        "positions": [
                            {
                                "trading_symbol": "NIFTY25OCTFUT",
                                "exchange": "NFO",
                                "segment": "FNO",
                                "quantity": 5,
                                "net_price": 1950000,  # In paise
                                "credit_quantity": 5,
                                "debit_quantity": 0,
                                "credit_price": 1950000,
                                "product": "MIS",
                                "symbol_isin": "NIFTYFUT",
                            }
                        ]
                    },
                },
            ),
        ]
        mock_get_oa_symbol.side_effect = [
            None,  # For RELIANCE (cash), no conversion needed
            "NIFTY25OCTFUT_OA",  # For NIFTY (FNO), converted
        ]

        result, status_code = get_positions(TEST_AUTH_TOKEN)

        assert status_code == 200
        assert result["status"] == "success"
        assert len(result["data"]) == 2
        assert result["data"][0]["symbol"] == "RELIANCE"
        assert result["data"][0]["exchange"] == "NSE_EQ"
        assert result["data"][0]["average_price"] == 2500.00
        assert result["data"][1]["symbol"] == "NIFTY25OCTFUT_OA"
        assert result["data"][1]["exchange"] == "NSE_FO"
        assert result["data"][1]["average_price"] == 19500.00
        assert mock_client.get.call_count == 2
        assert mock_get_oa_symbol.call_count == 2

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    def test_get_positions_api_error(self, mock_get_client):
        """Test get_positions with an API error."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "Server error", request=httpx.Request("GET", "http://test.com"), response=httpx.Response(500)
        )

        result, status_code = get_positions(TEST_AUTH_TOKEN)
        assert status_code == 500
        assert result["status"] == "error"
        assert "Error fetching positions" in result["message"]
        assert result["data"] == []

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    def test_get_holdings_success(self, mock_get_client):
        """Test successful retrieval of holdings."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {
            "status": "SUCCESS",
            "payload": {
                "holdings": [
                    {
                        "trading_symbol": "RELIANCE",
                        "exchange": "NSE",
                        "isin": "INE002A01018",
                        "quantity": 10,
                        "average_price": 2400.00,
                        "last_price": 2500.00,
                        "close_price": 2490.00,
                        "pnl": 1000.00,
                        "day_change": 50.00,
                        "day_change_percentage": 2.0,
                        "value": 25000.00,
                        "company_name": "Reliance Industries Ltd",
                        "token": "INE002A01018",
                        "t1_quantity": 0,
                        "realised_pnl": 0,
                        "unrealised_pnl": 1000.00,
                    }
                ]
            },
        }

        result, status_code = get_holdings(TEST_AUTH_TOKEN)

        assert status_code == 200
        assert result["status"] == "success"
        assert len(result["data"]) == 1
        assert result["data"][0]["symbol"] == "RELIANCE"
        assert result["data"][0]["exchange"] == "NSE"
        assert result["data"][0]["average_price"] == 2400.00
        assert result["data"][0]["unrealised"] == 1000.00
        mock_client.get.assert_called_once_with(
            "https://api.groww.in/v1/portfolio/holdings",
            headers={
                "Authorization": f"Bearer {TEST_AUTH_TOKEN}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    def test_get_holdings_api_error(self, mock_get_client):
        """Test get_holdings with an API error."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.return_value.status_code = 401
        mock_client.get.return_value.json.return_value = {"message": "Unauthorized"}

        result, status_code = get_holdings(TEST_AUTH_TOKEN)
        assert status_code == 401
        assert result["status"] == "error"
        assert "Unauthorized" in result["message"]
        assert result["data"] == []

    @patch("app.web.broker.broker.groww.api.order_api.get_positions")
    @patch("app.web.broker.broker.groww.api.order_api.get_br_symbol")
    def test_get_open_position_found(self, mock_get_br_symbol, mock_get_positions):
        """Test getting an open position when it exists."""
        mock_get_br_symbol.return_value = TEST_GROWW_SYMBOL
        mock_get_positions.return_value = (
            {
                "data": [
                    {
                        "tradingsymbol": TEST_GROWW_SYMBOL,
                        "exchange": "NSE_EQ",
                        "product": "CNC",
                        "net_quantity": 10,
                    }
                ]
            },
            200,
        )

        net_qty = get_open_position(TEST_OPENALGO_SYMBOL, TEST_EXCHANGE, "CNC", TEST_AUTH_TOKEN)
        assert net_qty == "10"
        mock_get_br_symbol.assert_called_once_with(TEST_OPENALGO_SYMBOL, TEST_EXCHANGE)
        mock_get_positions.assert_called_once_with(TEST_AUTH_TOKEN)

    @patch("app.web.broker.broker.groww.api.order_api.get_positions")
    @patch("app.web.broker.broker.groww.api.order_api.get_br_symbol")
    def test_get_open_position_not_found(self, mock_get_br_symbol, mock_get_positions):
        """Test getting an open position when it does not exist."""
        mock_get_br_symbol.return_value = TEST_GROWW_SYMBOL
        mock_get_positions.return_value = ({"data": []}, 200)

        net_qty = get_open_position(TEST_OPENALGO_SYMBOL, TEST_EXCHANGE, "CNC", TEST_AUTH_TOKEN)
        assert net_qty == "0"
        mock_get_br_symbol.assert_called_once_with(TEST_OPENALGO_SYMBOL, TEST_EXCHANGE)
        mock_get_positions.assert_called_once_with(TEST_AUTH_TOKEN)

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    @patch("app.web.broker.broker.groww.api.order_api.db_session")
    @patch("app.web.broker.broker.groww.api.order_api.SymToken")
    @patch("app.web.broker.broker.groww.api.order_api.format_openalgo_to_groww_symbol")
    def test_direct_place_order_api_success(
        self, mock_format_symbol, mock_symtoken, mock_db_session, mock_get_client
    ):
        """Test successful order placement."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.post.return_value.status_code = 200
        mock_client.post.return_value.json.return_value = {
            "status": "SUCCESS",
            "payload": {"groww_order_id": TEST_GROWW_ORDER_ID, "order_status": "PLACED"},
        }
        mock_format_symbol.return_value = TEST_GROWW_SYMBOL
        mock_db_session.return_value.__enter__.return_value.query.return_value.filter_by.return_value.first.return_value = MagicMock(
            brsymbol=TEST_GROWW_SYMBOL
        )

        order_data = {
            "symbol": TEST_OPENALGO_SYMBOL,
            "exchange": TEST_EXCHANGE,
            "quantity": 10,
            "action": "BUY",
            "pricetype": "MARKET",
            "product": "CNC",
        }
        res, response_data, order_id = direct_place_order_api(order_data, TEST_AUTH_TOKEN)

        assert res.status == 200
        assert response_data["groww_order_id"] == TEST_GROWW_ORDER_ID
        assert response_data["order_status"] == "PLACED"
        assert order_id == TEST_GROWW_ORDER_ID
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert kwargs["json"]["trading_symbol"] == TEST_GROWW_SYMBOL
        assert kwargs["json"]["quantity"] == 10
        assert kwargs["json"]["transaction_type"] == "BUY"
        assert kwargs["json"]["order_type"] == "MARKET"

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    @patch("app.web.broker.broker.groww.api.order_api.db_session")
    @patch("app.web.broker.broker.groww.api.order_api.SymToken")
    @patch("app.web.broker.broker.groww.api.order_api.format_openalgo_to_groww_symbol")
    def test_direct_place_order_api_api_failure(
        self, mock_format_symbol, mock_symtoken, mock_db_session, mock_get_client
    ):
        """Test order placement when API returns a failure status."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.post.return_value.status_code = 200
        mock_client.post.return_value.json.return_value = {
            "status": "FAILED",
            "message": "Order rejected",
        }
        mock_format_symbol.return_value = TEST_GROWW_SYMBOL
        mock_db_session.return_value.__enter__.return_value.query.return_value.filter_by.return_value.first.return_value = MagicMock(
            brsymbol=TEST_GROWW_SYMBOL
        )

        order_data = {
            "symbol": TEST_OPENALGO_SYMBOL,
            "exchange": TEST_EXCHANGE,
            "quantity": 10,
            "action": "BUY",
            "pricetype": "MARKET",
            "product": "CNC",
        }
        res, response_data, order_id = direct_place_order_api(order_data, TEST_AUTH_TOKEN)

        assert res.status == 400
        assert response_data["status"] == "error"
        assert "Order rejected" in response_data["message"]
        assert order_id is None

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    @patch("app.web.broker.broker.groww.api.order_api.get_open_position")
    @patch("app.web.broker.broker.groww.api.order_api.place_order_api")
    def test_place_smartorder_api_no_action_needed(
        self, mock_place_order_api, mock_get_open_position, mock_get_client
    ):
        """Test smart order placement when no action is needed (position matches target)."""
        mock_get_open_position.return_value = "10"  # Current position
        order_data = {
            "symbol": TEST_OPENALGO_SYMBOL,
            "exchange": TEST_EXCHANGE,
            "product": "CNC",
            "position_size": 10,  # Target position
            "quantity": 0, # No fresh order
        }
        res, response_data, order_id = place_smartorder_api(order_data, TEST_AUTH_TOKEN)

        assert res is None
        assert response_data["status"] == "success"
        assert "No action needed" in response_data["message"]
        assert order_id is None
        mock_get_open_position.assert_called_once_with(TEST_OPENALGO_SYMBOL, TEST_EXCHANGE, "CNC", TEST_AUTH_TOKEN)
        mock_place_order_api.assert_not_called()

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    @patch("app.web.broker.broker.groww.api.order_api.get_open_position")
    @patch("app.web.broker.broker.groww.api.order_api.place_order_api")
    def test_place_smartorder_api_close_long_position(
        self, mock_place_order_api, mock_get_open_position, mock_get_client
    ):
        """Test smart order to close a long position."""
        mock_get_open_position.return_value = "10"  # Current long position
        mock_place_order_api.return_value = (MagicMock(status=200), {"status": "SUCCESS"}, TEST_GROWW_ORDER_ID)

        order_data = {
            "symbol": TEST_OPENALGO_SYMBOL,
            "exchange": TEST_EXCHANGE,
            "product": "CNC",
            "position_size": 0,  # Target to close
        }
        res, response_data, order_id = place_smartorder_api(order_data, TEST_AUTH_TOKEN)

        assert res.status == 200
        assert response_data["status"] == "SUCCESS"
        assert order_id == TEST_GROWW_ORDER_ID
        mock_get_open_position.assert_called_once_with(TEST_OPENALGO_SYMBOL, TEST_EXCHANGE, "CNC", TEST_AUTH_TOKEN)
        mock_place_order_api.assert_called_once()
        args, kwargs = mock_place_order_api.call_args
        assert args[0]["action"] == "SELL"
        assert args[0]["quantity"] == "10"

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    @patch("app.web.broker.broker.groww.api.order_api.get_positions")
    @patch("app.web.broker.broker.groww.api.order_api.get_br_symbol")
    @patch("app.web.broker.broker.groww.api.order_api.place_order_api")
    def test_close_all_positions_success(
        self, mock_place_order_api, mock_get_br_symbol, mock_get_positions, mock_get_client
    ):
        """Test successful closing of all positions."""
        mock_get_positions.return_value = (
            {
                "data": [
                    {
                        "tradingsymbol": TEST_OPENALGO_SYMBOL,
                        "exchange": "NSE_EQ",
                        "product": "CNC",
                        "net_quantity": 10,
                        "segment": "EQ",
                    },
                    {
                        "tradingsymbol": "NIFTY25OCTFUT",
                        "exchange": "NSE_FO",
                        "product": "MIS",
                        "net_quantity": -5,
                        "segment": "FO",
                    },
                ]
            },
            200,
        )
        mock_get_br_symbol.side_effect = [
            TEST_GROWW_SYMBOL,  # For SBIN
            "NIFTY25OCTFUT",  # For NIFTY
        ]
        mock_place_order_api.return_value = (MagicMock(status=200), {"status": "SUCCESS"}, TEST_GROWW_ORDER_ID)

        result, status_code = close_all_positions(token=None, auth=TEST_AUTH_TOKEN)

        assert status_code == 200
        assert result["status"] == "success"
        assert "Squared off 2 positions" in result["message"]
        assert len(result["detailed_results"]) == 2
        assert result["detailed_results"][0]["status"] == "success"
        assert result["detailed_results"][0]["action"] == "SELL"
        assert result["detailed_results"][0]["quantity"] == 10
        assert result["detailed_results"][1]["status"] == "success"
        assert result["detailed_results"][1]["action"] == "BUY"
        assert result["detailed_results"][1]["quantity"] == 5
        assert mock_get_positions.call_count == 1
        assert mock_place_order_api.call_count == 2

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    @patch("app.web.broker.broker.groww.api.order_api.get_order_book")
    def test_cancel_order_success(self, mock_get_order_book, mock_get_client):
        """Test successful cancellation of an order."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.post.return_value.status_code = 200
        mock_client.post.return_value.json.return_value = {
            "status": "SUCCESS",
            "payload": {"groww_order_id": TEST_GROWW_ORDER_ID, "order_status": "CANCELLED"},
        }
        mock_get_order_book.return_value = (
            {
                "data": [
                    {
                        "groww_order_id": TEST_GROWW_ORDER_ID,
                        "segment": "CASH",
                        "order_status": "OPEN",
                        "symbol": TEST_OPENALGO_SYMBOL,
                        "exchange": TEST_EXCHANGE,
                    }
                ]
            },
            200,
        )

        result, status_code = cancel_order(TEST_GROWW_ORDER_ID, TEST_AUTH_TOKEN)

        assert status_code == 200
        assert result["status"] == "success"
        assert result["orderid"] == TEST_GROWW_ORDER_ID
        assert result["order_status"] == "CANCELLED"
        assert "Order cancelled successfully" in result["message"]
        assert result["symbol"] == TEST_OPENALGO_SYMBOL
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert kwargs["json"]["groww_order_id"] == TEST_GROWW_ORDER_ID
        assert kwargs["json"]["segment"] == TEST_SEGMENT_CASH

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    @patch("app.web.broker.broker.groww.api.order_api.get_order_book")
    def test_cancel_order_fno_detection(self, mock_get_order_book, mock_get_client):
        """Test cancellation of an FNO order with automatic segment detection."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.post.return_value.status_code = 200
        mock_client.post.return_value.json.return_value = {
            "status": "SUCCESS",
            "payload": {"groww_order_id": "GLTFO_123", "order_status": "CANCELLED"},
        }
        mock_get_order_book.return_value = ({"data": []}, 200) # No order in book

        result, status_code = cancel_order("GLTFO_123", TEST_AUTH_TOKEN)

        assert status_code == 200
        assert result["status"] == "success"
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert kwargs["json"]["segment"] == TEST_SEGMENT_FNO

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    @patch("app.web.broker.broker.groww.api.order_api.get_order_book")
    def test_direct_modify_order_success(self, mock_get_order_book, mock_get_client):
        """Test successful modification of an order."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.post.return_value.status_code = 200
        mock_client.post.return_value.json.return_value = {
            "status": "SUCCESS",
            "payload": {"groww_order_id": TEST_GROWW_ORDER_ID, "order_status": "MODIFIED"},
        }
        mock_get_order_book.return_value = (
            {
                "data": [
                    {
                        "groww_order_id": TEST_GROWW_ORDER_ID,
                        "order_type": "LIMIT",
                        "segment": "CASH",
                    }
                ]
            },
            200,
        )

        order_data = {
            "orderid": TEST_GROWW_ORDER_ID,
            "quantity": 20,
            "price": 155.0,
            "pricetype": "LIMIT",
            "exchange": TEST_EXCHANGE,
        }
        res, response_data = direct_modify_order(order_data, TEST_AUTH_TOKEN)

        assert res.status == 200
        assert response_data["status"] == "success"
        assert response_data["order_status"] == "MODIFIED"
        assert response_data["orderid"] == TEST_GROWW_ORDER_ID
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert kwargs["json"]["groww_order_id"] == TEST_GROWW_ORDER_ID
        assert kwargs["json"]["quantity"] == 20
        assert kwargs["json"]["price"] == 155.0
        assert kwargs["json"]["order_type"] == "LIMIT"
        assert kwargs["json"]["segment"] == TEST_SEGMENT_CASH

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    @patch("app.web.broker.broker.groww.api.order_api.get_order_book")
    def test_direct_modify_order_api_failure(self, mock_get_order_book, mock_get_client):
        """Test order modification when API returns a failure status."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.post.return_value.status_code = 400
        mock_client.post.return_value.json.return_value = {
            "status": "FAILED",
            "message": "Invalid order ID",
        }
        mock_get_order_book.return_value = ({"data": []}, 200)

        order_data = {
            "orderid": TEST_GROWW_ORDER_ID,
            "quantity": 20,
            "price": 155.0,
            "pricetype": "LIMIT",
            "exchange": TEST_EXCHANGE,
        }
        res, response_data = direct_modify_order(order_data, TEST_AUTH_TOKEN)

        assert res.status == 200 # Still returns 200 for consistency with UI
        assert response_data["status"] == "success" # Still returns success for consistency
        assert "Order modification request submitted" in response_data["message"]
        assert "Invalid order ID" in response_data["details"]

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    @patch("app.web.broker.broker.groww.api.order_api.get_order_book")
    @patch("app.web.broker.broker.groww.api.order_api.cancel_order")
    def test_cancel_all_orders_api_success(self, mock_cancel_order, mock_get_order_book, mock_get_client):
        """Test successful cancellation of all open orders."""
        mock_get_order_book.return_value = (
            {
                "data": [
                    {
                        "groww_order_id": "ORDER_1",
                        "order_status": "OPEN",
                        "segment": "CASH",
                        "symbol": "RELIANCE",
                        "exchange": "NSE",
                    },
                    {
                        "groww_order_id": "ORDER_2",
                        "order_status": "PENDING",
                        "segment": "FNO",
                        "symbol": "NIFTY25OCTFUT",
                        "exchange": "NFO",
                    },
                ]
            },
            200,
        )
        mock_cancel_order.side_effect = [
            ({"status": "success", "order_status": "CANCELLED", "symbol": "RELIANCE"}, 200),
            ({"status": "success", "order_status": "CANCELLED", "symbol": "NIFTY25OCTFUT"}, 200),
        ]

        cancelled_orders, failed_to_cancel = cancel_all_orders_api({}, TEST_AUTH_TOKEN)

        assert len(cancelled_orders) == 2
        assert len(failed_to_cancel) == 0
        assert cancelled_orders[0]["order_id"] == "ORDER_1"
        assert cancelled_orders[1]["order_id"] == "ORDER_2"
        mock_get_order_book.assert_called_once_with(TEST_AUTH_TOKEN)
        assert mock_cancel_order.call_count == 2

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    @patch("app.web.broker.broker.groww.api.order_api.get_order_book")
    @patch("app.web.broker.broker.groww.api.order_api.cancel_order")
    def test_cancel_all_orders_api_partial_failure(self, mock_cancel_order, mock_get_order_book, mock_get_client):
        """Test cancellation of all open orders with partial failures."""
        mock_get_order_book.return_value = (
            {
                "data": [
                    {
                        "groww_order_id": "ORDER_1",
                        "order_status": "OPEN",
                        "segment": "CASH",
                        "symbol": "RELIANCE",
                        "exchange": "NSE",
                    },
                    {
                        "groww_order_id": "ORDER_2",
                        "order_status": "PENDING",
                        "segment": "FNO",
                        "symbol": "NIFTY25OCTFUT",
                        "exchange": "NFO",
                    },
                ]
            },
            200,
        )
        mock_cancel_order.side_effect = [
            ({"status": "success", "order_status": "CANCELLED", "symbol": "RELIANCE"}, 200),
            ({"status": "error", "message": "API error"}, 500),
        ]

        cancelled_orders, failed_to_cancel = cancel_all_orders_api({}, TEST_AUTH_TOKEN)

        assert len(cancelled_orders) == 1
        assert len(failed_to_cancel) == 1
        assert cancelled_orders[0]["order_id"] == "ORDER_1"
        assert failed_to_cancel[0]["order_id"] == "ORDER_2"
        mock_get_order_book.assert_called_once_with(TEST_AUTH_TOKEN)
        assert mock_cancel_order.call_count == 2

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    @patch("app.web.broker.broker.groww.api.order_api.get_order_book")
    def test_get_order_trades_success(self, mock_get_order_book, mock_get_client):
        """Test successful retrieval of trades for a specific order."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {
            "status": "SUCCESS",
            "payload": {
                "trade_list": [
                    {
                        "groww_trade_id": "TRADE_1",
                        "groww_order_id": TEST_GROWW_ORDER_ID,
                        "trading_symbol": TEST_GROWW_SYMBOL,
                        "quantity": 10,
                        "price": 15000,  # In paise
                        "trade_date_time": "2023-01-01T10:00:00",
                        "transaction_type": "BUY",
                        "product": "CNC",
                        "exchange": "NSE",
                        "segment": "CASH",
                    }
                ]
            },
        }
        mock_get_order_book.return_value = (
            {
                "data": [
                    {
                        "groww_order_id": TEST_GROWW_ORDER_ID,
                        "segment": "CASH",
                        "filled_quantity": 10,
                        "trading_symbol": TEST_GROWW_SYMBOL,
                        "exchange": TEST_EXCHANGE,
                        "product": "CNC",
                        "transaction_type": "BUY",
                        "price": 15000,
                        "status": "FILLED",
                    }
                ]
            },
            200,
        )

        result, status_code = get_order_trades(TEST_GROWW_ORDER_ID, TEST_AUTH_TOKEN)

        assert status_code == 200
        assert result["status"] == "success"
        assert len(result["trades"]) == 1
        assert result["trades"][0]["order_id"] == TEST_GROWW_ORDER_ID
        assert result["trades"][0]["quantity"] == 10
        assert result["trades"][0]["price"] == 15000
        mock_client.get.assert_called_once()
        args, kwargs = mock_client.get.call_args
        assert kwargs["url"].startswith("https://api.groww.in/v1/order/trades/")
        assert "segment=CASH" in kwargs["url"]

    @patch("app.web.broker.broker.groww.api.order_api.get_httpx_client")
    @patch("app.web.broker.broker.groww.api.order_api.get_order_book")
    def test_get_order_trades_fno_synthetic(self, mock_get_order_book, mock_get_client):
        """Test retrieval of trades for FNO order with synthetic trade creation on 404."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.return_value.status_code = 404  # Simulate 404 for FNO trades
        mock_client.get.return_value.json.return_value = {"error": "Not Found"}
        mock_get_order_book.return_value = (
            {
                "data": [
                    {
                        "groww_order_id": "GLTFO_123",
                        "segment": "FNO",
                        "filled_quantity": 5,
                        "trading_symbol": "NIFTY25OCTFUT",
                        "exchange": "NFO",
                        "product": "MIS",
                        "transaction_type": "SELL",
                        "price": 1950000,
                        "status": "EXECUTED",
                    }
                ]
            },
            200,
        )

        result, status_code = get_order_trades("GLTFO_123", TEST_AUTH_TOKEN, segment=TEST_SEGMENT_FNO)

        assert status_code == 200
        assert result["status"] == "success"
        assert result["synthetic"] is True
        assert len(result["trades"]) == 1
        assert result["trades"][0]["trade_id"].startswith("synthetic_")
        assert result["trades"][0]["order_id"] == "GLTFO_123"
        assert result["trades"][0]["quantity"] == 5
        assert result["trades"][0]["price"] == 1950000
