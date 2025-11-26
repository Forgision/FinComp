import asyncio
import json
import random
from typing import Dict, Any

from app.web.websocket.base_adapter import BaseBrokerWebSocketAdapter
from app.utils.logging import logger


class DummyBrokerWebSocketAdapter(BaseBrokerWebSocketAdapter):
    """
    Dummy broker adapter for development and testing.
    Simulates real-time market data updates.
    """

    def __init__(self):
        super().__init__()
        self.running = False
        self.simulation_task = None
        self.subscribed_symbols = set()

    def initialize(self, broker_name, user_id, auth_data=None):
        logger.info(f"Initializing DummyBrokerWebSocketAdapter for user {user_id}")
        return {"success": True}

    def connect(self):
        logger.info("DummyBrokerWebSocketAdapter connected")
        self.connected = True
        self.running = True
        self.simulation_task = asyncio.create_task(self._simulate_market_data())
        return {"success": True}

    def disconnect(self):
        logger.info("DummyBrokerWebSocketAdapter disconnected")
        self.connected = False
        self.running = False
        if self.simulation_task:
            self.simulation_task.cancel()
            try:
                asyncio.get_event_loop().run_until_complete(self.simulation_task)
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

    def subscribe(self, symbol, exchange, mode=2, depth_level=5):
        logger.info(f"Subscribing to {exchange}:{symbol} (Mode: {mode})")
        self.subscribed_symbols.add((symbol, exchange))
        return self._create_success_response(
            "Subscribed successfully", actual_depth=depth_level
        )

    def unsubscribe(self, symbol, exchange, mode=2):
        logger.info(f"Unsubscribing from {exchange}:{symbol}")
        if (symbol, exchange) in self.subscribed_symbols:
            self.subscribed_symbols.remove((symbol, exchange))
        return self._create_success_response("Unsubscribed successfully")

    async def _simulate_market_data(self):
        """
        Background task to simulate market data updates
        """
        while self.running:
            try:
                for symbol, exchange in list(self.subscribed_symbols):
                    # Generate dummy LTP
                    ltp = 1000 + random.uniform(-10, 10)

                    data = {
                        "symbol": symbol,
                        "exchange": exchange,
                        "ltp": round(ltp, 2),
                        "change": round(random.uniform(-5, 5), 2),
                        "percent_change": round(random.uniform(-1, 1), 2),
                        "volume": int(random.uniform(1000, 100000)),
                        "timestamp": asyncio.get_event_loop().time(),
                    }

                    # Publish to ZeroMQ
                    # Topic format: {EXCHANGE}_{SYMBOL}_{MODE}
                    # Ensure symbol doesn't contain underscores that might confuse the parser,
                    # or rely on the parser handling it (which it might not if it splits by _)
                    # For NIFTY 50 it's fine (space).
                    topic = f"{exchange}_{symbol}_LTP"
                    self.publish_market_data(topic, data)

                await asyncio.sleep(1)  # Update every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in dummy market data simulation: {e}")
                await asyncio.sleep(1)
