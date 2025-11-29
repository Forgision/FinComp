import asyncio
import zmq
import zmq.asyncio
from app.core.config import settings
from app.utils.logging import logger


class DataServiceClient:
    def __init__(self):
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.address = f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_DATA_REQ_PORT}"
        self.socket.connect(self.address)
        self.lock = asyncio.Lock()
        logger.info(f"DataServiceClient connected to {self.address}")

    async def subscribe(self, symbol: str, exchange: str = "NSE", mode: int = 2):
        """
        Send subscribe request to DataService.
        """
        async with self.lock:
            try:
                # DataService expects {"action": "subscribe", "symbol": symbol, "exchange": exchange, "mode": mode}
                request = {
                    "action": "subscribe",
                    "symbol": symbol,
                    "exchange": exchange,
                    "mode": mode,
                }
                await self.socket.send_json(request)
                response = await self.socket.recv_json()
                return response
            except Exception as e:
                logger.error(f"Error subscribing to {symbol}: {e}")
                # If we get an error, the socket might be in a bad state.
                # Ideally we should recreate it, but for now let's just return error.
                return {"status": "error", "message": str(e)}

    async def unsubscribe(self, symbol: str, exchange: str = "NSE", mode: int = 2):
        """
        Send unsubscribe request to DataService.
        """
        async with self.lock:
            try:
                request = {
                    "action": "unsubscribe",
                    "symbol": symbol,
                    "exchange": exchange,
                    "mode": mode,
                }
                await self.socket.send_json(request)
                response = await self.socket.recv_json()
                return response
            except Exception as e:
                logger.error(f"Error unsubscribing from {symbol}: {e}")
                return {"status": "error", "message": str(e)}

    def close(self):
        self.socket.close()
        self.context.term()
