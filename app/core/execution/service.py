import asyncio
import json
import threading
import time
from typing import Dict, Any, Optional

import zmq
import zmq.asyncio
from app.core.config import settings
from app.utils.logging import logger
from app.core.schemas.zmq_messages import ExecutionReport


class ExecutionService:
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
        self.router_socket = None

        # In-memory state (System of Record)
        self.orders = {}
        self.positions = {}
        self.trades = {}

    async def start(self):
        logger.info("Starting ExecutionService...")
        self.running = True

        # Initialize sockets
        self.pub_socket = self.context.socket(zmq.PUB)
        self.sub_socket = self.context.socket(zmq.SUB)
        self.router_socket = self.context.socket(zmq.ROUTER)

        pub_address = f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_EXECUTION_PUB_PORT}"
        router_address = f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_EXECUTION_ROUTER_PORT}"

        logger.info(f"ExecutionService binding PUB socket to {pub_address}")
        logger.info(f"ExecutionService binding ROUTER socket to {router_address}")

        try:
            self.pub_socket.bind(pub_address)
            self.router_socket.bind(router_address)
        except zmq.error.ZMQError as e:
            logger.error(f"ExecutionService failed to bind sockets: {e}", exc_info=True)
            raise

        # Subscribe to Algo Engine (Signals)
        algo_sub_address = f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_ALGO_PUB_PORT}"
        logger.info(f"ExecutionService subscribing to Signals at {algo_sub_address}")

        # Since Algo Engine might start later, we connect and subscription will happen when available
        self.sub_socket.connect(algo_sub_address)
        self.sub_socket.subscribe(b"orders.signal.")

        # Start loops
        await asyncio.gather(
            self._signal_listener_loop(),
            self._router_listener_loop()
        )

        logger.info("ExecutionService started")

    async def _signal_listener_loop(self):
        logger.info("ExecutionService signal listener loop started")
        while self.running:
            try:
                if await self.sub_socket.poll(timeout=1000):
                    msg = await self.sub_socket.recv_multipart()
                    if len(msg) >= 2:
                        topic = msg[0].decode()
                        payload = json.loads(msg[1].decode())
                        await self.process_signal(topic, payload)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"ExecutionService signal listener error: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _router_listener_loop(self):
        logger.info("ExecutionService router listener loop started")
        while self.running:
            try:
                if await self.router_socket.poll(timeout=500):
                    msg = await self.router_socket.recv_multipart()
                    if len(msg) < 3:
                        continue
                    identity = msg[0]
                    # msg[1] is empty frame usually
                    payload = json.loads(msg[2].decode())

                    response = await self.handle_request(payload)

                    await self.router_socket.send_multipart(
                        [identity, b"", json.dumps(response).encode()]
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"ExecutionService router listener error: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def process_signal(self, topic: str, payload: Dict[str, Any]):
        logger.info(f"ExecutionService received signal: {payload}")
        # Validate and execute
        # For now, just log and pretend we placed it

        # Emit fake execution report
        report = ExecutionReport(
            order_id=f"ord_{int(time.time())}",
            strategy_id=payload.get("strategy_id"),
            symbol=payload.get("symbol"),
            side=payload.get("signal_type"),
            status="PLACED",
            filled_qty=0,
            ts=time.time()
        )
        await self.publish_execution_report(report)

    async def handle_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        action = payload.get("action")
        if action == "get_orders":
            return {"status": "success", "data": list(self.orders.values())}
        return {"status": "error", "message": "Unknown action"}

    async def publish_execution_report(self, report: ExecutionReport):
        topic = f"orders.exec_report.{report.order_id}"
        try:
            await self.pub_socket.send_multipart(
                [topic.encode(), report.model_dump_json().encode()]
            )
        except Exception as e:
            logger.error(f"ExecutionService failed to publish report: {e}")

    async def stop(self):
        logger.info("Stopping ExecutionService...")
        self.running = False

        if self.pub_socket:
            self.pub_socket.close()
        if self.sub_socket:
            self.sub_socket.close()
        if self.router_socket:
            self.router_socket.close()

        self.context.term()
        logger.info("ExecutionService stopped")


def get_execution_service() -> ExecutionService:
    return ExecutionService()
