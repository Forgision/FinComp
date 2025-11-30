import asyncio
import json
import threading
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set

import zmq
import zmq.asyncio
from app.core.config import settings
from app.data.broker_manager import BrokerManager
from app.data.subscription_registry import SubscriptionRegistry
from app.utils.logging import logger

# Try to import register_market_data_callback, but handle circular import if necessary
# In Client mode, we might need this.
try:
    from app.core.services.websocket_service import register_market_data_callback
except ImportError:
    register_market_data_callback = None


class DataService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, mode: str = "SERVER"):
        if self._initialized:
            return

        self._initialized = True
        self.mode = mode.upper()
        self.running = False
        self.context = zmq.asyncio.Context()

        # --- Server Mode Components ---
        self.pub_socket = None
        self.rep_socket = None
        self.router_socket = None
        self.registry = None
        self.broker_manager = None

        # --- Client Mode Components ---
        self.sub_socket = None
        self.req_socket = None
        self.data_lock = threading.Lock()
        self.market_data_cache = {}
        # Subscribers for real-time updates {event_type: {callback_id: callback_function}}
        self.subscribers = defaultdict(dict)
        self.subscriber_id_counter = 0
        # User-specific data tracking {user_id: {symbol_key: last_access_time}}
        self.user_access_tracking = defaultdict(dict)
        # Performance metrics
        self.metrics = {
            "total_updates": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "last_cleanup": time.time(),
        }
        self.zmq_thread = None
        self.cleanup_thread = None

        if self.mode == "SERVER":
            self._init_server()
        else:
            self._init_client()
            self.start_client()

    def _init_server(self):
        self.pub_socket = self.context.socket(zmq.PUB)
        self.rep_socket = self.context.socket(zmq.REP)
        self.router_socket = self.context.socket(zmq.ROUTER)
        self.registry = SubscriptionRegistry()
        self.broker_manager = BrokerManager(on_tick=self.on_market_data)

    def _init_client(self):
        # Client uses standard ZMQ for the listener thread to avoid asyncio complexity in background thread
        # or we can use asyncio if we run it in the main loop.
        # To match MarketDataService behavior (background thread), we'll use standard ZMQ context for the listener.
        self.client_zmq_context = zmq.Context()
        self.sub_socket = self.client_zmq_context.socket(zmq.SUB)

        # For REQ (subscriptions), we can use the asyncio context
        self.req_socket = self.context.socket(zmq.REQ)

    async def start(self):
        self.running = True
        if self.mode == "SERVER":
            await self._start_server()
        else:
            self.start_client()

    async def _start_server(self):
        pub_address = f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_PORT}"
        rep_address = f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_DATA_REQ_PORT}"
        router_address = f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_DATA_ROUTER_PORT}"

        logger.info(f"Binding PUB socket to {pub_address}")
        logger.info(f"Binding REP socket to {rep_address}")
        logger.info(f"Binding ROUTER socket to {router_address}")

        try:
            self.pub_socket.bind(pub_address)
            self.rep_socket.bind(rep_address)
            self.router_socket.bind(router_address)
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind sockets: {e}", exc_info=True)
            raise

        # Start with dummy broker for now to ensure data flow
        await self.broker_manager.authorize("dummy", {}, "fallback")

        await asyncio.gather(self.handle_requests(), self.handle_history_requests())

    def start_client(self):
        # Connect to Server
        zmq_url = f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_PORT}"
        req_url = f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_DATA_REQ_PORT}"

        try:
            self.sub_socket.connect(zmq_url)
            self.sub_socket.subscribe("")  # Subscribe to all topics
            logger.info(f"DataService (Client) subscribed to ZMQ at {zmq_url}")

            self.req_socket.connect(req_url)
            logger.info(f"DataService (Client) connected to REQ at {req_url}")
        except Exception as e:
            logger.error(f"Failed to connect to ZMQ: {e}")

        # Start ZMQ listener thread
        self.zmq_thread = threading.Thread(target=self._zmq_listener_loop, daemon=True)
        self.zmq_thread.start()

        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

        logger.info("DataService (Client) started")

    # --- Server Methods ---

    def on_market_data(self, tick: dict):
        """Callback from BrokerManager when new data is available."""
        mode = "LTP"
        if "open" in tick:
            mode = "QUOTE"

        topic = f"{self.broker_manager.broker_id or 'unknown'}_{tick.get('exchange', 'NSE')}_{tick['symbol']}_{mode}"
        asyncio.create_task(self._publish(topic, tick))

    async def _publish(self, topic: str, tick: dict):
        try:
            await self.pub_socket.send_multipart(
                [topic.encode(), json.dumps(tick).encode()]
            )
        except Exception as e:
            logger.error(f"Error publishing data: {e}", exc_info=True)

    async def handle_requests(self):
        logger.info("Starting request handler (REP)...")
        while self.running:
            try:
                if await self.rep_socket.poll(timeout=500):
                    message = await self.rep_socket.recv_json()
                    action = message.get("action")
                else:
                    continue

                response = {"status": "error", "message": "Invalid action"}

                if action == "authorize":
                    broker_id = message.get("broker_id")
                    auth_data = message.get("auth_data", {})
                    mode = message.get("mode", "main")
                    success = await self.broker_manager.authorize(
                        broker_id, auth_data, mode
                    )
                    response = {
                        "status": "success" if success else "error",
                        "message": f"Authorization {'success' if success else 'failed'}",
                    }

                elif action == "subscribe":
                    symbol = message.get("symbol")
                    exchange = message.get("exchange", "NSE")
                    mode = message.get("mode", 2)
                    if symbol:
                        if self.registry.add(symbol):
                            await self.broker_manager.subscribe(symbol, exchange, mode)
                        response = {
                            "status": "success",
                            "message": f"Subscribed to {symbol}",
                        }
                    else:
                        response = {"status": "error", "message": "Symbol required"}

                elif action == "unsubscribe":
                    symbol = message.get("symbol")
                    exchange = message.get("exchange", "NSE")
                    mode = message.get("mode", 2)
                    if symbol:
                        if self.registry.remove(symbol):
                            await self.broker_manager.unsubscribe(
                                symbol, exchange, mode
                            )
                        response = {
                            "status": "success",
                            "message": f"Unsubscribed from {symbol}",
                        }
                    else:
                        response = {"status": "error", "message": "Symbol required"}

                await self.rep_socket.send_json(response)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error handling request: {e}", exc_info=True)
                try:
                    await self.rep_socket.send_json(
                        {"status": "error", "message": str(e)}
                    )
                except Exception:
                    pass

    async def handle_history_requests(self):
        logger.debug("Starting history handler (ROUTER)...")
        while self.running:
            try:
                if await self.router_socket.poll(timeout=500):
                    msg = await self.router_socket.recv_multipart()
                    if len(msg) < 3:
                        continue
                    identity = msg[0]
                    response = {
                        "status": "error",
                        "message": "History not implemented yet",
                    }
                    await self.router_socket.send_multipart(
                        [identity, b"", json.dumps(response).encode()]
                    )
                else:
                    continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error handling history request: {e}", exc_info=True)

    # --- Client Methods (Ported from MarketDataService) ---

    def _zmq_listener_loop(self):
        """Background thread to listen for ZMQ messages."""
        logger.info("Starting ZMQ listener loop")
        while self.running:
            try:
                if self.sub_socket.poll(1000):
                    msg = self.sub_socket.recv_multipart()
                    if len(msg) >= 2:
                        payload = json.loads(msg[1].decode("utf-8"))
                        self.process_market_data(payload)
            except zmq.ZMQError as e:
                logger.error(f"ZMQ Error in listener loop: {e}")
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in ZMQ listener loop: {e}")
                time.sleep(0.1)

    def process_market_data(self, data: Dict[str, Any]) -> None:
        """Process incoming market data from ZMQ or WebSocket."""
        try:
            symbol = data.get("symbol")
            exchange = data.get("exchange")
            # Infer mode if not present, similar to on_market_data
            mode = data.get("mode")  # 1=LTP, 2=Quote, 3=Depth

            # If mode is missing, try to infer or default
            if mode is None:
                if "depth" in data:
                    mode = 3
                elif "open" in data:
                    mode = 2
                else:
                    mode = 1

            market_data = (
                data  # The payload itself might be the data or inside 'data' key
            )
            # Check if 'data' key exists, if so use it, else assume root is data
            if "data" in data:
                market_data = data["data"]

            if not symbol or not exchange:
                return

            symbol_key = f"{exchange}:{symbol}"
            timestamp = int(time.time())

            with self.data_lock:
                if symbol_key not in self.market_data_cache:
                    self.market_data_cache[symbol_key] = {"last_update": timestamp}

                cache_entry = self.market_data_cache[symbol_key]

                if mode == 1:  # LTP
                    cache_entry["ltp"] = {
                        "value": market_data.get("ltp", 0),
                        "timestamp": market_data.get("timestamp", timestamp),
                        "volume": market_data.get("volume", 0),
                    }
                elif mode == 2:  # Quote
                    cache_entry["quote"] = {
                        "open": market_data.get("open", 0),
                        "high": market_data.get("high", 0),
                        "low": market_data.get("low", 0),
                        "close": market_data.get("close", 0),
                        "ltp": market_data.get("ltp", 0),
                        "volume": market_data.get("volume", 0),
                        "timestamp": market_data.get("timestamp", timestamp),
                        "change": market_data.get("change", 0),
                        "percent_change": market_data.get("percent_change", 0),
                    }
                    # Also update LTP from quote
                    cache_entry["ltp"] = {
                        "value": market_data.get("ltp", 0),
                        "timestamp": market_data.get("timestamp", timestamp),
                        "volume": market_data.get("volume", 0),
                    }
                elif mode == 3:  # Depth
                    cache_entry["depth"] = {
                        "buy": market_data.get("depth", {}).get("buy", []),
                        "sell": market_data.get("depth", {}).get("sell", []),
                        "ltp": market_data.get("ltp", 0),
                        "timestamp": market_data.get("timestamp", timestamp),
                    }

                cache_entry["last_update"] = timestamp
                self.metrics["total_updates"] += 1

            self._broadcast_update(symbol_key, mode, data)

        except Exception as e:
            logger.exception(f"Error processing market data: {e}")

    def _broadcast_update(
        self, symbol_key: str, mode: int, data: Dict[str, Any]
    ) -> None:
        mode_to_event = {1: "ltp", 2: "quote", 3: "depth"}
        event_type = mode_to_event.get(mode, "all")

        with self.data_lock:
            subscribers = list(self.subscribers[event_type].values())
            all_subscribers = list(self.subscribers["all"].values())

        for subscriber in subscribers + all_subscribers:
            try:
                if subscriber["filter"] and symbol_key not in subscriber["filter"]:
                    continue
                subscriber["callback"](data)
            except Exception as e:
                logger.error(f"Error in subscriber callback: {e}")

    def get_ltp(self, symbol: str, exchange: str) -> Optional[Dict[str, Any]]:
        symbol_key = f"{exchange}:{symbol}"
        with self.data_lock:
            self.metrics["cache_hits"] += 1
            if symbol_key in self.market_data_cache:
                return self.market_data_cache[symbol_key].get("ltp")
        self.metrics["cache_misses"] += 1
        return None

    def get_quote(self, symbol: str, exchange: str) -> Optional[Dict[str, Any]]:
        symbol_key = f"{exchange}:{symbol}"
        with self.data_lock:
            self.metrics["cache_hits"] += 1
            if symbol_key in self.market_data_cache:
                return self.market_data_cache[symbol_key].get("quote")
        self.metrics["cache_misses"] += 1
        return None

    def get_market_depth(self, symbol: str, exchange: str) -> Optional[Dict[str, Any]]:
        symbol_key = f"{exchange}:{symbol}"
        with self.data_lock:
            self.metrics["cache_hits"] += 1
            if symbol_key in self.market_data_cache:
                return self.market_data_cache[symbol_key].get("depth")
        self.metrics["cache_misses"] += 1
        return None

    def subscribe_to_updates(
        self,
        event_type: str,
        callback: Callable,
        filter_symbols: Optional[Set[str]] = None,
    ) -> int:
        with self.data_lock:
            self.subscriber_id_counter += 1
            subscriber_id = self.subscriber_id_counter
            self.subscribers[event_type][subscriber_id] = {
                "callback": callback,
                "filter": filter_symbols,
            }
        logger.info(f"Added subscriber {subscriber_id} for {event_type} updates")
        return subscriber_id

    def unsubscribe_from_updates(self, subscriber_id: int) -> bool:
        with self.data_lock:
            for event_type in self.subscribers:
                if subscriber_id in self.subscribers[event_type]:
                    del self.subscribers[event_type][subscriber_id]
                    return True
        return False

    def register_user_callback(self, username: str) -> bool:
        """Register market data callback for a specific user via websocket_service."""
        if register_market_data_callback:

            def user_callback(data):
                try:
                    self.process_market_data(data)
                except Exception as e:
                    logger.error(f"Error processing market data in callback: {e}")

            return register_market_data_callback(username, user_callback)
        return False

    def _cleanup_loop(self) -> None:
        while self.running:
            try:
                time.sleep(300)
                current_time = time.time()
                stale_threshold = 3600
                with self.data_lock:
                    stale_symbols = [
                        k
                        for k, v in self.market_data_cache.items()
                        if current_time - v.get("last_update", 0) > stale_threshold
                    ]
                    for k in stale_symbols:
                        del self.market_data_cache[k]
                    self.metrics["last_cleanup"] = current_time
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def stop(self):
        logger.debug("Stopping DataService...")
        self.running = False

        if self.mode == "SERVER":
            if self.broker_manager:
                await self.broker_manager.stop()
            self.pub_socket.close()
            self.rep_socket.close()
            self.router_socket.close()
        else:
            if self.zmq_thread:
                self.zmq_thread.join(timeout=1)
            if self.cleanup_thread:
                self.cleanup_thread.join(timeout=1)
            self.sub_socket.close()
            self.req_socket.close()
            self.client_zmq_context.term()

        self.context.term()
        logger.info("DataService stopped.")


# Global instance helper
def get_data_service(mode: str = "CLIENT") -> DataService:
    """Get the global DataService instance, initializing it if necessary."""
    return DataService(mode=mode)


if __name__ == "__main__":
    # When running as script, default to SERVER mode
    service = DataService(mode="SERVER")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(service.start())
    except KeyboardInterrupt:
        loop.run_until_complete(service.stop())
    finally:
        loop.close()
