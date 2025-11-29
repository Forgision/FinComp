import asyncio
import json
import zmq
import zmq.asyncio
from app.core.config import settings
from app.data.broker_manager import BrokerManager
from app.data.subscription_registry import SubscriptionRegistry
from app.utils.logging import logger


class DataService:
    def __init__(self):
        self.context = zmq.asyncio.Context()
        self.pub_socket = self.context.socket(zmq.PUB)
        self.rep_socket = self.context.socket(zmq.REP)
        self.router_socket = self.context.socket(zmq.ROUTER)

        self.running = False
        self.registry = SubscriptionRegistry()
        self.broker_manager = BrokerManager(on_tick=self.on_market_data)

    async def start(self):
        pub_address = f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_PORT}"
        rep_address = f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_DATA_REQ_PORT}"
        router_address = f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_DATA_ROUTER_PORT}"

        logger.info(f"Binding PUB socket to {pub_address}")
        logger.info(f"Binding REP socket to {rep_address}")
        logger.info(f"Binding ROUTER socket to {router_address}")

        try:
            self.pub_socket.bind(pub_address)
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind PUB socket: {e}", exc_info=True)
            raise

        try:
            self.rep_socket.bind(rep_address)
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind REP socket: {e}", exc_info=True)
            raise

        try:
            self.router_socket.bind(router_address)
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind ROUTER socket: {e}", exc_info=True)
            raise

        self.running = True

        # Start with dummy broker by default or wait for auth?
        # DATA_Service.md says "Waiting for Auth".
        # But for dev convenience, maybe we want to start dummy if no auth?
        # The doc says "Initialization: Data Service starts and initializes the Broker Manager in a 'Passive' state."
        # So we wait.

        await asyncio.gather(self.handle_requests(), self.handle_history_requests())

    def on_market_data(self, tick: dict):
        """Callback from BrokerManager when new data is available."""
        topic = f"market_data.{tick['symbol']}"
        # Since this is called from the event loop (via call_soon_threadsafe in BrokerManager),
        # we can schedule the async send.
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
                message = await self.rep_socket.recv_json()
                action = message.get("action")

                response = {"status": "error", "message": "Invalid action"}

                if action == "authorize":
                    broker_id = message.get("broker_id")
                    auth_data = message.get("auth_data", {})
                    mode = message.get("mode", "main")

                    success = await self.broker_manager.authorize(
                        broker_id, auth_data, mode
                    )
                    if success:
                        response = {
                            "status": "success",
                            "message": f"Authorized {broker_id}",
                        }
                    else:
                        response = {
                            "status": "error",
                            "message": f"Failed to authorize {broker_id}",
                        }

                elif action == "subscribe":
                    symbol = message.get("symbol")
                    if symbol:
                        if self.registry.add(symbol):
                            await self.broker_manager.subscribe(symbol)
                        response = {
                            "status": "success",
                            "message": f"Subscribed to {symbol}",
                        }
                    else:
                        response = {"status": "error", "message": "Symbol required"}

                elif action == "unsubscribe":
                    symbol = message.get("symbol")
                    if symbol:
                        if self.registry.remove(symbol):
                            await self.broker_manager.unsubscribe(symbol)
                        response = {
                            "status": "success",
                            "message": f"Unsubscribed from {symbol}",
                        }
                    else:
                        response = {"status": "error", "message": "Symbol required"}

                await self.rep_socket.send_json(response)

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
                # Router receives [identity, empty, message]
                msg = await self.router_socket.recv_multipart()
                if len(msg) < 3:
                    continue

                identity = msg[0]
                # msg[1] is empty delimiter
                _payload = json.loads(msg[2].decode())

                # TODO: Implement history fetch logic
                # For now, return a dummy response or not implemented
                response = {"status": "error", "message": "History not implemented yet"}

                await self.router_socket.send_multipart(
                    [identity, b"", json.dumps(response).encode()]
                )

            except Exception as e:
                logger.error(f"Error handling history request: {e}", exc_info=True)

    def stop(self):
        logger.debug("Stopping DataService...")
        self.running = False
        asyncio.create_task(self.broker_manager.stop())
        self.pub_socket.close()
        self.rep_socket.close()
        self.router_socket.close()
        self.context.term()
        logger.info("DataService stopped.")


if __name__ == "__main__":
    service = DataService()
    try:
        asyncio.run(service.start())
    except KeyboardInterrupt:
        service.stop()
