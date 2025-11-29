import asyncio
import logging
import random
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


# TODO: Add support for other brokers websockets e.g UpstoxWebSocketClient for upstox,
class BrokerManager:
    def __init__(self, on_tick: Callable[[Dict], None]):
        self.on_tick = on_tick
        self.active_broker = None
        self.broker_id = None
        self.is_dummy = False
        self.running = False
        self._dummy_task = None
        self.subscribed_symbols = set()
        self.loop = asyncio.get_event_loop()

    async def authorize(
        self, broker_id: str, auth_data: Dict[str, Any], mode: str = "main"
    ) -> bool:
        logger.info(f"Authorizing broker: {broker_id}, mode: {mode}")

        if self.active_broker or self.is_dummy:
            await self.stop()

        self.broker_id = broker_id

        if broker_id in ["dummy", "dummy_broker"] or mode == "fallback":
            self.is_dummy = True
            self.running = True
            self._dummy_task = asyncio.create_task(self._run_dummy_stream())
            logger.info("Dummy broker activated")
            return True

        if broker_id == "zerodha":
            try:
                from app.core.brokers.zerodha.streaming.zerodha_websocket import (
                    ZerodhaWebSocket,
                )

                # Assuming API Key is in settings or auth_data
                api_key = auth_data.get("api_key") or settings.BROKER_API_KEY
                access_token = auth_data.get("access_token")

                if not api_key or not access_token:
                    logger.error("Missing api_key or access_token for Zerodha")
                    return False

                self.active_broker = ZerodhaWebSocket(
                    api_key=api_key,
                    access_token=access_token,
                    on_ticks=self._on_broker_tick,
                )
                self.active_broker.start()
                self.is_dummy = False
                self.running = True
                logger.info("Zerodha broker activated")
                return True
            except ImportError:
                logger.error("Zerodha broker module not found")
                return False
            except Exception as e:
                logger.error(f"Failed to initialize Zerodha broker: {e}")
                return False

        logger.error(f"Unsupported broker: {broker_id}")
        return False

    async def subscribe(self, symbol: str, exchange: str = "NSE", mode: int = 2):
        # Store as tuple (symbol, exchange, mode)
        self.subscribed_symbols.add((symbol, exchange, mode))
        if self.is_dummy:
            logger.info(f"Dummy subscribed to {symbol} ({exchange}, {mode})")
            return

        if self.active_broker and self.broker_id == "zerodha":
            token = self._get_token_for_symbol(symbol)
            if token:
                # ZerodhaWebSocket.subscribe_tokens takes a list of ints
                self.active_broker.subscribe_tokens([token])
            else:
                logger.warning(f"Could not resolve token for symbol: {symbol}")

    async def unsubscribe(self, symbol: str, exchange: str = "NSE", mode: int = 2):
        # Remove tuple
        if (symbol, exchange, mode) in self.subscribed_symbols:
            self.subscribed_symbols.discard((symbol, exchange, mode))

        if self.is_dummy:
            logger.info(f"Dummy unsubscribed from {symbol}")
            return

        if self.active_broker and self.broker_id == "zerodha":
            token = self._get_token_for_symbol(symbol)
            if token:
                self.active_broker.unsubscribe([token])

    def _on_broker_tick(self, ticks: List[Dict]):
        # This is called from the broker's thread
        for tick in ticks:
            normalized_tick = self._normalize_tick(tick)
            if normalized_tick:
                # Schedule the callback on the main loop
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(self.on_tick, normalized_tick)

    def _normalize_tick(self, tick: Dict) -> Optional[Dict]:
        # Normalize Zerodha tick to standard format
        token = tick.get("instrument_token")
        symbol = self._get_symbol_for_token(token)

        if not symbol:
            return None

        # Basic normalization - adjust fields as per DATA_Service.md
        return {
            "symbol": symbol,
            "exchange": "NSE",  # Default to NSE for now
            "timestamp": datetime.now().timestamp(),  # Ideally use tick timestamp if available
            "ltp": tick.get("last_price"),
            "open": tick.get("ohlc", {}).get("open"),
            "high": tick.get("ohlc", {}).get("high"),
            "low": tick.get("ohlc", {}).get("low"),
            "close": tick.get("ohlc", {}).get("close"),
            "volume": tick.get("volume_traded"),
        }

    async def _run_dummy_stream(self):
        logger.info("Starting dummy data stream")
        while self.running and self.is_dummy:
            if not self.subscribed_symbols:
                await asyncio.sleep(1)
                continue

            for sub in list(self.subscribed_symbols):
                # Handle both old string format (if any lingering) and new tuple format
                if isinstance(sub, tuple):
                    symbol, exchange, mode = sub
                else:
                    symbol = sub
                    exchange = "NSE"
                    mode = 2

                # Use realistic prices for indices
                if symbol == "NIFTY 50":
                    base_price = 24350.0
                elif symbol == "BANKNIFTY":
                    base_price = 52100.0
                else:
                    base_price = 1000.0

                # Add some random fluctuation
                price = round(base_price + random.uniform(-50, 50), 2)

                # Calculate change and percent change
                # We use base_price as the "previous close" for dummy data consistency
                change = round(price - base_price, 2)
                percent_change = round((change / base_price) * 100, 2)

                tick = {
                    "symbol": symbol,
                    "exchange": exchange,
                    "timestamp": datetime.now().timestamp(),
                    "ltp": price,
                    "open": round(price * 0.99, 2),
                    "high": round(price * 1.01, 2),
                    "low": round(price * 0.98, 2),
                    "close": price,
                    "volume": random.randint(1000, 100000),
                    "change": change,
                    "percent_change": percent_change,
                }
                self.on_tick(tick)

            await asyncio.sleep(1)

    async def stop(self):
        self.running = False
        if self._dummy_task:
            self._dummy_task.cancel()
            try:
                await self._dummy_task
            except asyncio.CancelledError:
                pass
            self._dummy_task = None

        if self.active_broker:
            if hasattr(self.active_broker, "stop"):
                self.active_broker.stop()
            self.active_broker = None

    def _get_token_for_symbol(self, symbol: str) -> Optional[int]:
        # Placeholder for mapping logic
        if symbol.isdigit():
            return int(symbol)
        # TODO: Implement real mapping
        # For testing, if symbol is like "INFY", we can't guess the token.
        # But if the user passes "256265" (INFY token), it works.
        return None

    def _get_symbol_for_token(self, token: int) -> Optional[str]:
        # Placeholder
        return str(token)
