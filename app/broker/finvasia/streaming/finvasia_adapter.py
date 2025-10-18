import json
import threading
import time
from typing import Any, Dict, List, Optional

from app.db.auth_db import get_auth_token
from app.web.websocket.base_adapter import BaseBrokerWebSocketAdapter
from app.web.websocket.mapping import SymbolMapper

from app.core.config import settings
from app.utils.logging import logger

from .finvasia_mapping import FinvasiaExchangeMapper
from .finvasia_websocket import FinvasiaWebSocket

class Config:
    MAX_RECONNECT_ATTEMPTS = 10
    BASE_RECONNECT_DELAY = 5
    MAX_RECONNECT_DELAY = 60
    CACHE_COMPLETENESS_THRESHOLD = 0.3
    WEBSOCKET_TIMEOUT = 30
    MODE_LTP = 1
    MODE_QUOTE = 2
    MODE_DEPTH = 3
    MSG_AUTH = 'ck'
    MSG_TOUCHLINE_FULL = 'tf'
    MSG_TOUCHLINE_PARTIAL = 'tk'
    MSG_DEPTH_FULL = 'df'
    MSG_DEPTH_PARTIAL = 'dk'

class MarketDataCache:
    """NOTE: This is a placeholder implementation."""
    def __init__(self):
        self._cache = {}
        self._initialized_tokens = set()
        self._lock = threading.Lock()
        self.logger = logger
    def get(self, token: str) -> Dict[str, Any]:
        with self._lock:
            return self._cache.get(token, {}).copy()
    def update(self, token: str, data: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            cached_data = self._cache.get(token, {})
            merged_data = self._merge_data(cached_data, data, token)
            self._cache[token] = merged_data
            if token not in self._initialized_tokens:
                self._initialized_tokens.add(token)
                self._log_cache_initialization(token, data)
            return merged_data.copy()
    def clear(self, token: str = None) -> None:
        with self._lock:
            if token:
                self._cache.pop(token, None)
                self._initialized_tokens.discard(token)
                self.logger.info(f"Cleared cache for token {token}")
            else:
                cache_size = len(self._cache)
                self._cache.clear()
                self._initialized_tokens.clear()
                self.logger.info(f"Cleared all cached market data ({cache_size} tokens)")
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {'total_tokens': len(self._cache), 'initialized_tokens': len(self._initialized_tokens), 'tokens': list(self._cache.keys())}
    def _merge_data(self, cached: Dict, new: Dict, token: str) -> Dict:
        merged = cached.copy()
        for key, value in new.items():
            if self._should_preserve_cached_value(key, value, cached):
                continue
            merged[key] = value
        self._preserve_missing_fields(merged, new, cached)
        return merged
    def _should_preserve_cached_value(self, key: str, new_value: Any, cached: Dict) -> bool:
        if key in ['o', 'h', 'l', 'c', 'ap'] and self._is_zero_value(new_value):
            cached_value = cached.get(key)
            return cached_value is not None and not self._is_zero_value(cached_value)
        return False
    def _preserve_missing_fields(self, merged: Dict, new: Dict, cached: Dict) -> None:
        for key, value in cached.items():
            if key not in new:
                merged[key] = value
    def _is_zero_value(self, value: Any) -> bool:
        return value in [None, '', '0', 0, '0.0', 0.0]
    def _log_cache_initialization(self, token: str, data: Dict) -> None:
        basic_fields = ['lp', 'o', 'h', 'l', 'c', 'v', 'ap', 'pc', 'ltq', 'ltt', 'tbq', 'tsq']
        present_fields = sum(1 for field in basic_fields if field in data)
        completeness = present_fields / len(basic_fields)
        self.logger.info(f"Initializing cache for token {token} - {present_fields}/{len(basic_fields)} fields present ({completeness:.1%})")

class LTPNormalizer:
    @staticmethod
    def normalize(data: Dict[str, Any], msg_type: str) -> Dict[str, Any]:
        return {'mode': Config.MODE_LTP, 'ltp': safe_float(data.get('lp')), 'shoonya_timestamp': safe_int(data.get('ltt'))}

class QuoteNormalizer:
    @staticmethod
    def normalize(data: Dict[str, Any], msg_type: str) -> Dict[str, Any]:
        return {
            'mode': Config.MODE_QUOTE, 'ltp': safe_float(data.get('lp')), 'volume': safe_int(data.get('v')),
            'open': safe_float(data.get('o')), 'high': safe_float(data.get('h')), 'low': safe_float(data.get('l')),
            'close': safe_float(data.get('c')), 'average_price': safe_float(data.get('ap')),
            'percent_change': safe_float(data.get('pc')), 'last_quantity': safe_int(data.get('ltq')),
            'last_trade_time': data.get('ltt'), 'shoonya_timestamp': safe_int(data.get('ltt'))
        }

class DepthNormalizer:
    @staticmethod
    def normalize(data: Dict[str, Any], msg_type: str) -> Dict[str, Any]:
        result = {
            'mode': Config.MODE_DEPTH, 'ltp': safe_float(data.get('lp')), 'volume': safe_int(data.get('v')),
            'open': safe_float(data.get('o')), 'high': safe_float(data.get('h')), 'low': safe_float(data.get('l')),
            'close': safe_float(data.get('c')), 'average_price': safe_float(data.get('ap')),
            'percent_change': safe_float(data.get('pc')), 'last_quantity': safe_int(data.get('ltq')),
            'last_trade_time': data.get('ltt'), 'total_buy_quantity': safe_int(data.get('tbq')),
            'total_sell_quantity': safe_int(data.get('tsq')), 'shoonya_timestamp': safe_int(data.get('ltt'))
        }
        if msg_type in (Config.MSG_DEPTH_FULL, Config.MSG_DEPTH_PARTIAL):
            result['depth'] = {
                'buy': [{'price': safe_float(data.get(f'bp{i}')), 'quantity': safe_int(data.get(f'bq{i}')), 'orders': safe_int(data.get(f'bo{i}'))} for i in range(1, 6)],
                'sell': [{'price': safe_float(data.get(f'sp{i}')), 'quantity': safe_int(data.get(f'sq{i}')), 'orders': safe_int(data.get(f'so{i}'))} for i in range(1, 6)]
            }
            result['depth_level'] = 5
            result.update({
                'upper_circuit': safe_float(data.get('uc')), 'lower_circuit': safe_float(data.get('lc')),
                '52_week_high': safe_float(data.get('52h')), '52_week_low': safe_float(data.get('52l')),
                'total_traded_value': safe_int(data.get('toi'))
            })
        return result

class FinvasiaWebSocketAdapter(BaseBrokerWebSocketAdapter):
    """NOTE: This is a placeholder implementation."""
    def __init__(self):
        super().__init__()
        self.logger = logger
        self._setup_adapter()
        self._setup_market_cache()
        self._setup_connection_management()
        self._setup_normalizers()

    def _setup_adapter(self):
        self.user_id = None
        self.broker_name = "finvasia"
        self.ws_client = None

    def _setup_market_cache(self):
        self.market_cache = MarketDataCache()
        self.subscriptions = {}
        self.token_to_symbol = {}
        self.ws_subscription_refs = {}

    def _setup_connection_management(self):
        self.running = False
        self.connected = False
        self.lock = threading.Lock()
        self.reconnect_attempts = 0

    def _setup_normalizers(self):
        self.normalizers = {Config.MODE_LTP: LTPNormalizer(), Config.MODE_QUOTE: QuoteNormalizer(), Config.MODE_DEPTH: DepthNormalizer()}

    def initialize(self, broker_name: str, user_id: str, auth_data: Optional[Dict[str, str]] = None) -> None:
        self.user_id = user_id
        self.broker_name = broker_name
        api_key = settings.BROKER_API_KEY
        self.actid = api_key[:-2] if api_key and len(api_key) > 2 else api_key or user_id
        self.susertoken = get_auth_token(user_id)
        if not self.actid or not self.susertoken:
            raise ValueError(f"Missing Finvasia credentials for user {user_id}")
        self.logger.info(f"Using Finvasia credentials - User ID: {self.actid}")
        self.ws_client = FinvasiaWebSocket(
            user_id=self.actid, actid=self.actid, susertoken=self.susertoken,
            on_message=self._on_message, on_error=self._on_error, on_close=self._on_close, on_open=self._on_open
        )
        self.running = True

    def connect(self) -> None:
        if not self.ws_client:
            self.logger.error("WebSocket client not initialized. Call initialize() first.")
            return
        self.logger.info("Connecting to Finvasia WebSocket...")
        if self.ws_client.connect():
            self.connected = True
            self.reconnect_attempts = 0
            self.logger.info("Connected to Finvasia WebSocket successfully")
        else:
            raise ConnectionError("Failed to connect to Finvasia WebSocket")

    def disconnect(self) -> None:
        self.running = False
        with self.lock:
            self.subscriptions.clear()
            self.token_to_symbol.clear()
            self.ws_subscription_refs.clear()
            self.logger.info("Cleared all subscriptions and mappings")
        if self.ws_client:
            self.ws_client.stop()
            self.ws_client = None
        self.market_cache.clear()
        self.cleanup_zmq()
        self.connected = False
        self.logger.info("Disconnected from Finvasia WebSocket and cleaned up all resources")

    def subscribe(self, symbol: str, exchange: str, mode: int = Config.MODE_QUOTE, depth_level: int = 5) -> Dict[str, Any]:
        try:
            self.logger.info(f"[SUBSCRIBE] Request for {symbol}.{exchange} mode={mode}")
            if not self._validate_subscription_params(symbol, exchange, mode):
                return self._create_error_response("INVALID_PARAMS", "Invalid subscription parameters")
            token_info = self._get_token_info(symbol, exchange)
            if not token_info:
                return self._create_error_response("SYMBOL_NOT_FOUND", f"Symbol {symbol} not found")
            subscription = self._create_subscription(symbol, exchange, mode, depth_level, token_info)
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            correlation_id = f"{symbol}_{exchange}_{mode}_{unique_id}"
            base_correlation_id = f"{symbol}_{exchange}_{mode}"
            already_ws_subscribed = any(cid.startswith(base_correlation_id) for cid in self.subscriptions.keys())
            if already_ws_subscribed:
                self.logger.info(f"[SUBSCRIBE] WebSocket already subscribed for {base_correlation_id}, adding client subscription {correlation_id}")
            else:
                self.logger.info(f"[SUBSCRIBE] New WebSocket subscription needed for {correlation_id}")
            self._store_subscription(correlation_id, subscription)
            if self.connected:
                self._websocket_subscribe(subscription)
                if not already_ws_subscribed:
                    self.logger.info(f"[SUBSCRIBE] WebSocket subscription sent for {subscription['scrip']}")
            else:
                self.logger.warning(f"[SUBSCRIBE] Not connected, cannot subscribe to {subscription['scrip']}")
            self.logger.info(f"[SUBSCRIBE] Publishing to ZMQ port: {self.zmq_port}")
            self.logger.info(f"[SUBSCRIBE] Total active subscriptions: {len(self.subscriptions)}")
            return self._create_success_response(f'Subscribed to {symbol}.{exchange}', symbol=symbol, exchange=exchange, mode=mode)
        except Exception as e:
            self.logger.error(f"Subscription error for {symbol}.{exchange}: {e}")
            return self._create_error_response("SUBSCRIPTION_ERROR", str(e))

    def unsubscribe(self, symbol: str, exchange: str, mode: int = Config.MODE_QUOTE) -> Dict[str, Any]:
        base_correlation_id = f"{symbol}_{exchange}_{mode}"
        with self.lock:
            matching_subscriptions = [(cid, sub) for cid, sub in self.subscriptions.items() if cid.startswith(base_correlation_id)]
            if not matching_subscriptions:
                return self._create_error_response("NOT_SUBSCRIBED", f"Not subscribed to {symbol}.{exchange}")
            correlation_id, subscription = matching_subscriptions[0]
            is_last = len(matching_subscriptions) == 1
            del self.subscriptions[correlation_id]
            token = subscription['token']
            if not any(sub['token'] == token for sub in self.subscriptions.values()):
                self.token_to_symbol.pop(token, None)
            if is_last:
                scrip = subscription['scrip']
                if scrip in self.ws_subscription_refs:
                    if mode in [Config.MODE_LTP, Config.MODE_QUOTE]:
                        self.ws_subscription_refs[scrip]['touchline_count'] -= 1
                        if self.ws_subscription_refs[scrip]['touchline_count'] <= 0:
                            self._websocket_unsubscribe(subscription)
                    elif mode == Config.MODE_DEPTH:
                        self.ws_subscription_refs[scrip]['depth_count'] -= 1
                        if self.ws_subscription_refs[scrip]['depth_count'] <= 0:
                            self._websocket_unsubscribe(subscription)
        return self._create_success_response(f"Unsubscribed from {symbol}.{exchange}", symbol=symbol, exchange=exchange, mode=mode)

    def _validate_subscription_params(self, symbol: str, exchange: str, mode: int) -> bool:
        return symbol and exchange and mode in [Config.MODE_LTP, Config.MODE_QUOTE, Config.MODE_DEPTH]

    def _get_token_info(self, symbol: str, exchange: str) -> Optional[Dict]:
        self.logger.info(f"Looking up token for {symbol}.{exchange}")
        token_info = SymbolMapper.get_token_from_symbol(symbol, exchange)
        if token_info:
            self.logger.info(f"Token found: {token_info['token']}, brexchange: {token_info['brexchange']}")
        return token_info

    def _create_subscription(self, symbol: str, exchange: str, mode: int, depth_level: int, token_info: Dict) -> Dict:
        token = token_info['token']
        brexchange = token_info['brexchange']
        finvasia_exchange = FinvasiaExchangeMapper.to_finvasia_exchange(brexchange)
        scrip = f"{finvasia_exchange}|{token}"
        return {'symbol': symbol, 'exchange': exchange, 'mode': mode, 'depth_level': depth_level, 'token': token, 'scrip': scrip}

    def _store_subscription(self, correlation_id: str, subscription: Dict) -> None:
        with self.lock:
            self.subscriptions[correlation_id] = subscription
            self.token_to_symbol[subscription['token']] = (subscription['symbol'], subscription['exchange'])

    def _websocket_subscribe(self, subscription: Dict) -> None:
        scrip = subscription['scrip']
        mode = subscription['mode']
        if scrip not in self.ws_subscription_refs:
            self.ws_subscription_refs[scrip] = {'touchline_count': 0, 'depth_count': 0}
        if mode in [Config.MODE_LTP, Config.MODE_QUOTE]:
            if self.ws_subscription_refs[scrip]['touchline_count'] == 0:
                self.logger.info(f"First touchline subscription for {scrip}")
                self.ws_client.subscribe_touchline(scrip)
            self.ws_subscription_refs[scrip]['touchline_count'] += 1
        elif mode == Config.MODE_DEPTH:
            if self.ws_subscription_refs[scrip]['depth_count'] == 0:
                self.logger.info(f"First depth subscription for {scrip}")
                self.ws_client.subscribe_depth(scrip)
            self.ws_subscription_refs[scrip]['depth_count'] += 1

    def _websocket_unsubscribe(self, subscription: Dict) -> None:
        scrip = subscription['scrip']
        mode = subscription['mode']
        if scrip not in self.ws_subscription_refs:
            return
        if mode in [Config.MODE_LTP, Config.MODE_QUOTE]:
            self.ws_subscription_refs[scrip]['touchline_count'] -= 1
            if self.ws_subscription_refs[scrip]['touchline_count'] <= 0:
                self.logger.info(f"Last touchline subscription for {scrip}")
                self.ws_client.unsubscribe_touchline(scrip)
                self.ws_subscription_refs[scrip]['touchline_count'] = 0
        elif mode == Config.MODE_DEPTH:
            self.ws_subscription_refs[scrip]['depth_count'] -= 1
            if self.ws_subscription_refs[scrip]['depth_count'] <= 0:
                self.logger.info(f"Last depth subscription for {scrip}")
                self.ws_client.unsubscribe_depth(scrip)
                self.ws_subscription_refs[scrip]['depth_count'] = 0

    def _remove_subscription(self, correlation_id: str, subscription: Dict) -> None:
        token = subscription['token']
        scrip = subscription['scrip']
        if correlation_id in self.subscriptions:
            del self.subscriptions[correlation_id]
        if scrip in self.ws_subscription_refs and self.ws_subscription_refs[scrip]['touchline_count'] <= 0 and self.ws_subscription_refs[scrip]['depth_count'] <= 0:
            del self.ws_subscription_refs[scrip]
            self.logger.debug(f"Removed reference counts for {scrip}")
        if not any(sub.get('token') == token for sub in self.subscriptions.values()):
            if token in self.token_to_symbol:
                del self.token_to_symbol[token]
                self.logger.debug(f"Removed token mapping for {token}")
            self.market_cache.clear(token)

    def _on_open(self, ws):
        self.logger.info("Connected to Finvasia WebSocket")
        self.connected = True
        self._resubscribe_all()

    def _on_error(self, ws, error):
        self.logger.error(f"Finvasia WebSocket error: {error}")
        self._handle_websocket_error(error)

    def _on_close(self, ws, close_status_code, close_msg):
        self.logger.info(f"Finvasia WebSocket connection closed: {close_status_code} - {close_msg}")
        self.connected = False
        if self.running:
            self._schedule_reconnection()

    def _handle_websocket_error(self, error: Exception) -> None:
        self.logger.error(f"WebSocket error: {error}")
        if self.running:
            self._schedule_reconnection()

    def _schedule_reconnection(self) -> None:
        if self.reconnect_attempts >= Config.MAX_RECONNECT_ATTEMPTS:
            self.logger.error("Maximum reconnection attempts reached")
            self.running = False
            return
        delay = min(Config.BASE_RECONNECT_DELAY * (2 ** self.reconnect_attempts), Config.MAX_RECONNECT_DELAY)
        self.logger.info(f"Reconnecting in {delay}s (attempt {self.reconnect_attempts + 1})")
        threading.Timer(delay, self._attempt_reconnection).start()

    def _attempt_reconnection(self) -> None:
        self.reconnect_attempts += 1
        try:
            self.ws_client = FinvasiaWebSocket(
                user_id=self.actid, actid=self.actid, susertoken=self.susertoken,
                on_message=self._on_message, on_error=self._on_error, on_close=self._on_close, on_open=self._on_open
            )
            if self.ws_client.connect():
                self.connected = True
                self.reconnect_attempts = 0
                self.logger.info("Reconnected successfully")
            else:
                self.logger.error("Reconnection failed")
        except Exception as e:
            self.logger.error(f"Reconnection error: {e}")

    def _resubscribe_all(self):
        with self.lock:
            self.ws_subscription_refs = {}
            touchline_scrips = set()
            depth_scrips = set()
            for subscription in self.subscriptions.values():
                scrip = subscription['scrip']
                mode = subscription['mode']
                if scrip not in self.ws_subscription_refs:
                    self.ws_subscription_refs[scrip] = {'touchline_count': 0, 'depth_count': 0}
                if mode in [Config.MODE_LTP, Config.MODE_QUOTE]:
                    if scrip not in touchline_scrips:
                        touchline_scrips.add(scrip)
                    self.ws_subscription_refs[scrip]['touchline_count'] += 1
                elif mode == Config.MODE_DEPTH:
                    if scrip not in depth_scrips:
                        depth_scrips.add(scrip)
                    self.ws_subscription_refs[scrip]['depth_count'] += 1
            if touchline_scrips:
                scrip_list = '#'.join(touchline_scrips)
                self.ws_client.subscribe_touchline(scrip_list)
                self.logger.info(f"Resubscribed to {len(touchline_scrips)} touchline scrips")
            if depth_scrips:
                scrip_list = '#'.join(depth_scrips)
                self.ws_client.subscribe_depth(scrip_list)
                self.logger.info(f"Resubscribed to {len(depth_scrips)} depth scrips")

    def _on_message(self, ws, message):
        self.logger.debug(f"[RAW_MESSAGE] {message}")
        try:
            data = json.loads(message)
            msg_type = data.get('t')
            if msg_type == Config.MSG_AUTH:
                self.logger.info(f"Authentication response: {data}")
                return
            if msg_type in (Config.MSG_TOUCHLINE_FULL, Config.MSG_TOUCHLINE_PARTIAL, Config.MSG_DEPTH_FULL, Config.MSG_DEPTH_PARTIAL):
                self._process_market_message(data)
            else:
                self.logger.debug(f"Unknown message type {msg_type}: {data}")
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}, message: {message}")
        except Exception as e:
            self.logger.error(f"Message processing error: {e}", exc_info=True)

    def _process_market_message(self, data: Dict[str, Any]) -> None:
        try:
            msg_type = data.get('t')
            token = data.get('tk')
            if not self._is_valid_market_message(msg_type, token):
                return
            symbol, exchange = self._get_symbol_info(token)
            if not symbol:
                return
            matching_subscriptions = self._find_matching_subscriptions(token)
            for subscription in matching_subscriptions:
                if self._should_process_message(msg_type, subscription['mode']):
                    self._process_subscription_message(data, subscription, symbol, exchange)
        except Exception as e:
            self.logger.error(f"Message processing error: {e}")

    def _is_valid_market_message(self, msg_type: str, token: str) -> bool:
        return msg_type and token and token in self.token_to_symbol

    def _get_symbol_info(self, token: str) -> tuple:
        return self.token_to_symbol.get(token, (None, None))

    def _find_matching_subscriptions(self, token: str) -> List[Dict]:
        with self.lock:
            return [sub for sub in self.subscriptions.values() if sub.get('token') == token]

    def _should_process_message(self, msg_type: str, mode: int) -> bool:
        touchline_messages = {Config.MSG_TOUCHLINE_FULL, Config.MSG_TOUCHLINE_PARTIAL}
        depth_messages = {Config.MSG_DEPTH_FULL, Config.MSG_DEPTH_PARTIAL}
        if mode in [Config.MODE_LTP, Config.MODE_QUOTE]:
            return msg_type in touchline_messages
        elif mode == Config.MODE_DEPTH:
            return msg_type in depth_messages
        return False

    def _process_subscription_message(self, data: Dict, subscription: Dict, symbol: str, exchange: str) -> None:
        mode = subscription['mode']
        msg_type = data.get('t')
        normalized_data = self._normalize_market_data(data, msg_type, mode)
        normalized_data.update({'symbol': symbol, 'exchange': exchange, 'timestamp': int(time.time() * 1000)})
        mode_str = {Config.MODE_LTP: 'LTP', Config.MODE_QUOTE: 'QUOTE', Config.MODE_DEPTH: 'DEPTH'}[mode]
        topic = f"{exchange}_{symbol}_{mode_str}"
        self.logger.debug(f"[{mode_str}] Publishing data for {symbol}")
        self.publish_market_data(topic, normalized_data)

    def _normalize_market_data(self, data: Dict[str, Any], msg_type: str, mode: int) -> Dict[str, Any]:
        token = data.get('tk')
        if token:
            data = self.market_cache.update(token, data)
        normalizer = self.normalizers.get(mode)
        if not normalizer:
            self.logger.error(f"No normalizer found for mode {mode}")
            return {}
        return normalizer.normalize(data, msg_type)

    def get_market_data_cache_stats(self) -> Dict[str, Any]:
        return self.market_cache.get_stats()

    def clear_market_data_cache(self, token: str = None) -> None:
        self.market_cache.clear(token)

def safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == '' or value == '-':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == '' or value == '-':
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default