import asyncio
import json
import threading
import time
from typing import Dict, Any, Optional

import zmq
import zmq.asyncio
from app.core.config import settings
from app.utils.logging import logger


class AlgoService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.running = False
        self.context = zmq.asyncio.Context()

        self.pub_socket = None
        self.sub_socket = None

        # Placeholder for strategy manager
        self.strategies = {}

    async def start(self):
        logger.info("Starting AlgoService...")
        self.running = True

        # Initialize sockets
        self.pub_socket = self.context.socket(zmq.PUB)
        self.sub_socket = self.context.socket(zmq.SUB)

        pub_address = f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_ALGO_PUB_PORT}"
        logger.info(f"AlgoService binding PUB socket to {pub_address}")
        try:
            self.pub_socket.bind(pub_address)
        except zmq.error.ZMQError as e:
            logger.error(f"AlgoService failed to bind PUB socket: {e}", exc_info=True)
            raise

        # Subscribe to Data Engine (Market Data) and Execution Engine (Reports)
        data_sub_address = f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_PORT}"
        execution_sub_address = f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_EXECUTION_PUB_PORT}"

        logger.info(f"AlgoService subscribing to Market Data at {data_sub_address}")
        self.sub_socket.connect(data_sub_address)
        self.sub_socket.subscribe(b"md.") # Subscribe to all market data topics

        logger.info(f"AlgoService subscribing to Execution Reports at {execution_sub_address}")
        self.sub_socket.connect(execution_sub_address)
        self.sub_socket.subscribe(b"orders.exec_report.")

        # Start listener loop
        asyncio.create_task(self._listener_loop())

        logger.info("AlgoService started")

    async def _listener_loop(self):
        logger.info("AlgoService listener loop started")
        while self.running:
            try:
                if await self.sub_socket.poll(timeout=1000):
                    msg = await self.sub_socket.recv_multipart()
                    if len(msg) >= 2:
                        topic = msg[0].decode()
                        payload = json.loads(msg[1].decode())
                        await self.process_message(topic, payload)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"AlgoService listener error: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def process_message(self, topic: str, payload: Dict[str, Any]):
        # logger.debug(f"AlgoService received message on {topic}")
        if topic.startswith("md."):
            await self.handle_market_data(topic, payload)
        elif topic.startswith("orders.exec_report."):
            await self.handle_execution_report(topic, payload)

    async def handle_market_data(self, topic: str, payload: Dict[str, Any]):
        # Pass to strategies
        pass

    async def handle_execution_report(self, topic: str, payload: Dict[str, Any]):
        # Update strategy state
        pass

    async def publish_signal(self, signal: Dict[str, Any]):
        topic = f"orders.signal.{signal.get('strategy_id', 'unknown')}"
        try:
            await self.pub_socket.send_multipart(
                [topic.encode(), json.dumps(signal).encode()]
            )
        except Exception as e:
            logger.error(f"AlgoService failed to publish signal: {e}")

    async def stop(self):
        logger.info("Stopping AlgoService...")
        self.running = False

        if self.pub_socket:
            self.pub_socket.close()
        if self.sub_socket:
            self.sub_socket.close()

        self.context.term()
        logger.info("AlgoService stopped")


def get_algo_service() -> AlgoService:
    return AlgoService()
