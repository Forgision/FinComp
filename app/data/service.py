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

        # Start with dummy broker for now to ensure data flow
        await self.broker_manager.authorize("dummy", {}, "fallback")

        await asyncio.gather(self.handle_requests(), self.handle_history_requests())

    def on_market_data(self, tick: dict):
        """Callback from BrokerManager when new data is available."""
        # Format: BROKER_EXCHANGE_SYMBOL_MODE
        # Mode is assumed to be LTP (1) or QUOTE (2). Let's use LTP for now or infer from data.
        # If tick has OHLC, it's effectively a Quote.
        mode = "LTP"
        if "open" in tick:
            mode = "QUOTE"

        topic = f"{self.broker_manager.broker_id or 'unknown'}_{tick.get('exchange', 'NSE')}_{tick['symbol']}_{mode}"
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
                if await self.rep_socket.poll(timeout=500):
                    logger.debug("Waiting for request...")
                    message = await self.rep_socket.recv_json()
                    logger.debug(f"Received request: {message}")
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
                logger.info("Request handler cancelled")
                break
            except zmq.error.ContextTerminated:
                logger.info("ZMQ Context terminated")
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
                    # Router receives [identity, empty, message]
                    msg = await self.router_socket.recv_multipart()
                    if len(msg) < 3:
                        continue

                    identity = msg[0]
                    # msg[1] is empty delimiter
                    _payload = json.loads(msg[2].decode())

                    # TODO: Implement history fetch logic
                    # For now, return a dummy response or not implemented
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
                logger.info("History handler cancelled")
                break
            except zmq.error.ContextTerminated:
                logger.info("ZMQ Context terminated")
                break
            except Exception as e:
                logger.error(f"Error handling history request: {e}", exc_info=True)

    async def stop(self):
        logger.debug("Stopping DataService...")
        self.running = False
        logger.debug("Stopping broker manager...")
        await self.broker_manager.stop()
        logger.debug("Broker manager stopped.")

        # Set LINGER to 0 to avoid hanging on close
        self.pub_socket.setsockopt(zmq.LINGER, 0)
        self.rep_socket.setsockopt(zmq.LINGER, 0)
        self.router_socket.setsockopt(zmq.LINGER, 0)

        logger.debug("Closing sockets...")
        self.pub_socket.close()
        self.rep_socket.close()
        self.router_socket.close()
        logger.debug("Sockets closed.")

        logger.debug("Terminating context...")
        self.context.term()
        logger.info("DataService stopped.")


if __name__ == "__main__":
    service = DataService()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(service.start())
    except KeyboardInterrupt:
        loop.run_until_complete(service.stop())
    finally:
        loop.close()
