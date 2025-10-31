import asyncio as aio
import json
import signal
import socket
import threading

import websockets
import zmq
import zmq.asyncio
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.models.auth_db import get_broker_name, verify_api_key
from app.db.session import get_db
from app.utils.logging import highlight_url, logger
from app.web.websocket.broker_factory import create_broker_adapter
from app.web.websocket.port_check import is_port_in_use


class WebSocketProxy:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        if is_port_in_use(host, port, wait_time=2.0):
            error_msg = (
                f"WebSocket port {port} is already in use on {host}.\n"
                f"This port is required for SDK compatibility (see strategies/ltp_example.py).\n"
                f"Please:\n"
                f"1. Stop any other OpenAlgo instances running on port {port}\n"
                f"2. Kill any processes using port {port}: lsof -ti:{port} | xargs kill -9\n"
                f"3. Or wait for the port to be released\n"
                f"Cannot start WebSocket server with port switching as it would break SDK clients."
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        self.clients = {}
        self.subscriptions = {}
        self.broker_adapters = {}
        self.user_mapping = {}
        self.user_broker_mapping = {}
        self.running = False
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.SUB)
        ZMQ_HOST = settings.ZMQ_HOST
        ZMQ_PORT = settings.ZMQ_PORT
        self.socket.connect(f"tcp://{ZMQ_HOST}:{ZMQ_PORT}")
        self.socket.setsockopt(zmq.SUBSCRIBE, b"")

    async def start(self):
        self.running = True
        try:
            loop = aio.get_running_loop()
            loop.create_task(self.zmq_listener())
            stop = aio.Future()

            async def monitor_shutdown():
                while self.running:
                    await aio.sleep(0.5)
                stop.set_result(None)
            monitor_task = aio.create_task(monitor_shutdown())
            try:
                if threading.current_thread() is threading.main_thread():
                    try:
                        for sig in (signal.SIGINT, signal.SIGTERM):
                            loop.add_signal_handler(sig, stop.set_result, None)
                        logger.info("Signal handlers registered successfully")
                    except (NotImplementedError, RuntimeError) as e:
                        logger.info(f"Signal handlers not registered: {e}. Using fallback mechanism.")
                else:
                    logger.info("Running in a non-main thread. Signal handlers will not be used.")
            except RuntimeError:
                logger.info("No running event loop found for signal handlers")
            highlighted_address = highlight_url(f"{self.host}:{self.port}")
            logger.info(f"Starting WebSocket server on {highlighted_address}")
            try:
                self.server = await websockets.serve(
                    self.handle_client,
                    self.host,
                    self.port,
                    reuse_port=True if hasattr(socket, 'SO_REUSEPORT') else False
                )
                highlighted_success_address = highlight_url(f"{self.host}:{self.port}")
                logger.info(f"WebSocket server successfully started on {highlighted_success_address}")
                await stop
                monitor_task.cancel()
                try:
                    await monitor_task
                except aio.CancelledError:
                    pass
            except Exception as e:
                logger.exception(f"Failed to start WebSocket server: {e}")
                raise
        except Exception as e:
            logger.exception(f"Error in start method: {e}")
            raise

    async def stop(self):
        logger.info("Stopping WebSocket server...")
        self.running = False
        try:
            if hasattr(self, 'server') and self.server:
                try:
                    logger.info("Closing WebSocket server...")
                    try:
                        self.server.close()
                        await self.server.wait_closed()
                        logger.info("WebSocket server closed and port released")
                    except RuntimeError as e:
                        if "attached to a different loop" in str(e):
                            logger.warning(f"WebSocket server cleanup skipped due to event loop mismatch: {e}")
                            try:
                                self.server.close()
                            except Exception:
                                pass
                        else:
                            raise
                except Exception as e:
                    logger.error(f"Error closing WebSocket server: {e}")
            close_tasks = []
            for client_id, websocket in self.clients.items():
                try:
                    if hasattr(websocket, 'open') and websocket.open:
                        close_tasks.append(websocket.close())
                except Exception as e:
                    logger.error(f"Error preparing to close client {client_id}: {e}")
            if close_tasks:
                try:
                    await aio.wait_for(
                        aio.gather(*close_tasks, return_exceptions=True),
                        timeout=2.0
                    )
                except aio.TimeoutError:
                    logger.warning("Timeout waiting for client connections to close")
            for user_id, adapter in self.broker_adapters.items():
                try:
                    adapter.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting adapter for user {user_id}: {e}")
            if hasattr(self, 'socket') and self.socket:
                try:
                    self.socket.setsockopt(zmq.LINGER, 0)
                    self.socket.close()
                except Exception as e:
                    logger.error(f"Error closing ZMQ socket: {e}")
            if hasattr(self, 'context') and self.context:
                try:
                    self.context.term()
                except Exception as e:
                    logger.error(f"Error terminating ZMQ context: {e}")
            logger.info("WebSocket server stopped and resources cleaned up")
        except Exception as e:
            logger.error(f"Error during WebSocket server stop: {e}")

    async def handle_client(self, websocket):
        client_id = id(websocket)
        self.clients[client_id] = websocket
        self.subscriptions[client_id] = set()
        path = getattr(websocket, 'path', '/unknown')
        logger.info(f"Client connected: {client_id} from path: {path}")
        try:
            async for message in websocket:
                try:
                    logger.debug(f"Received message from client {client_id}: {message}")
                    await self.process_client_message(client_id, message)
                except Exception as e:
                    logger.exception(f"Error processing message from client {client_id}: {e}")
                    try:
                        await self.send_error(client_id, "PROCESSING_ERROR", str(e))
                    except Exception:
                        pass
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Client disconnected: {client_id}, code: {e.code}, reason: {e.reason}")
        except Exception as e:
            logger.exception(f"Unexpected error handling client {client_id}: {e}")
        finally:
            await self.cleanup_client(client_id)

    async def cleanup_client(self, client_id):
        if client_id in self.clients:
            del self.clients[client_id]
        if client_id in self.subscriptions:
            subscriptions = self.subscriptions[client_id]
            for sub_json in subscriptions:
                try:
                    sub_info = json.loads(sub_json)
                    symbol = sub_info.get('symbol')
                    exchange = sub_info.get('exchange')
                    mode = sub_info.get('mode')
                    user_id = self.user_mapping.get(client_id)
                    if user_id and user_id in self.broker_adapters:
                        adapter = self.broker_adapters[user_id]
                        adapter.unsubscribe(symbol, exchange, mode)
                except json.JSONDecodeError as e:
                    logger.exception(f"Error parsing subscription: {sub_json}, Error: {e}")
                except Exception as e:
                    logger.exception(f"Error processing subscription: {e}")
                    continue
            del self.subscriptions[client_id]
        if client_id in self.user_mapping:
            user_id = self.user_mapping[client_id]
            is_last_client = all(other_user_id != user_id for other_client_id, other_user_id in self.user_mapping.items() if other_client_id != client_id)
            if is_last_client and user_id in self.broker_adapters:
                adapter = self.broker_adapters[user_id]
                broker_name = self.user_broker_mapping.get(user_id)
                if broker_name in ['flattrade', 'shoonya'] and hasattr(adapter, 'unsubscribe_all'):
                    logger.info(f"{broker_name.title()} adapter for user {user_id}: last client disconnected. Unsubscribing all symbols instead of disconnecting.")
                    adapter.unsubscribe_all()
                else:
                    logger.info(f"Last client for user {user_id} disconnected. Disconnecting {broker_name or 'unknown broker'} adapter.")
                    adapter.disconnect()
                    del self.broker_adapters[user_id]
                    if user_id in self.user_broker_mapping:
                        del self.user_broker_mapping[user_id]
            del self.user_mapping[client_id]

    async def process_client_message(self, client_id, message):
        try:
            data = json.loads(message)
            logger.debug(f"Parsed message from client {client_id}: {data}")
            action = data.get("action") or data.get("type")
            logger.info(f"Client {client_id} requested action: {action}")
            db = next(get_db())
            if action in ["authenticate", "auth"]:
                await self.authenticate_client(db, client_id, data)
            elif action == "subscribe":
                await self.subscribe_client(client_id, data)
            elif action in ["unsubscribe", "unsubscribe_all"]:
                await self.unsubscribe_client(client_id, data)
            elif action == "get_broker_info":
                await self.get_broker_info(client_id)
            elif action == "get_supported_brokers":
                await self.get_supported_brokers(client_id)
            else:
                logger.warning(f"Client {client_id} requested invalid action: {action}")
                await self.send_error(client_id, "INVALID_ACTION", f"Invalid action: {action}")
        except json.JSONDecodeError:
            logger.exception(f"Invalid JSON from client {client_id}: {message}")
            await self.send_error(client_id, "INVALID_JSON", "Invalid JSON message")
        except Exception as e:
            logger.exception(f"Error processing client message: {e}")
            await self.send_error(client_id, "SERVER_ERROR", str(e))

    async def authenticate_client(self, db: Session, client_id, data):
        api_key = data.get("api_key")
        if not api_key:
            await self.send_error(client_id, "AUTHENTICATION_ERROR", "API key is required")
            return
        user_id = verify_api_key(db, api_key)
        if not user_id:
            await self.send_error(client_id, "AUTHENTICATION_ERROR", "Invalid API key")
            return
        self.user_mapping[client_id] = user_id
        broker_name = get_broker_name(db, api_key)
        if not broker_name:
            await self.send_error(client_id, "BROKER_ERROR", "No broker configuration found for user")
            return
        self.user_broker_mapping[user_id] = broker_name
        if user_id not in self.broker_adapters:
            try:
                adapter = create_broker_adapter(broker_name)
                if not adapter:
                    await self.send_error(client_id, "BROKER_ERROR", f"Failed to create adapter for broker: {broker_name}")
                    return
                initialization_result = adapter.initialize(broker_name, user_id)
                if initialization_result and not initialization_result.get('success', True):
                    error_msg = initialization_result.get('error', 'Failed to initialize broker adapter')
                    await self.send_error(client_id, "BROKER_INIT_ERROR", error_msg)
                    return
                connect_result = adapter.connect()
                if connect_result and not connect_result.get('success', True):
                    error_msg = connect_result.get('error', 'Failed to connect to broker')
                    await self.send_error(client_id, "BROKER_CONNECTION_ERROR", error_msg)
                    return
                self.broker_adapters[user_id] = adapter
                logger.info(f"Successfully created and connected {broker_name} adapter for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to create broker adapter for {broker_name}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                await self.send_error(client_id, "BROKER_ERROR", str(e))
                return
        await self.send_message(client_id, {
            "type": "auth",
            "status": "success",
            "message": "Authentication successful",
            "broker": broker_name,
            "user_id": user_id,
            "supported_features": {"ltp": True, "quote": True, "depth": True}
        })

    async def get_supported_brokers(self, client_id):
        try:
            valid_brokers = settings.VALID_BROKERS.split(',')
            supported_brokers = [broker.strip() for broker in valid_brokers if broker.strip()]
            await self.send_message(client_id, {
                "type": "supported_brokers",
                "status": "success",
                "brokers": supported_brokers,
                "count": len(supported_brokers)
            })
        except Exception as e:
            logger.error(f"Error getting supported brokers: {e}")
            await self.send_error(client_id, "BROKER_LIST_ERROR", str(e))

    async def get_broker_info(self, client_id):
        if client_id not in self.user_mapping:
            await self.send_error(client_id, "NOT_AUTHENTICATED", "You must authenticate first")
            return
        user_id = self.user_mapping[client_id]
        broker_name = self.user_broker_mapping.get(user_id)
        if not broker_name:
            await self.send_error(client_id, "BROKER_ERROR", "Broker information not available")
            return
        adapter_status = "disconnected"
        if user_id in self.broker_adapters:
            adapter = self.broker_adapters[user_id]
            adapter_status = getattr(adapter, 'status', 'connected')
        await self.send_message(client_id, {
            "type": "broker_info",
            "status": "success",
            "broker": broker_name,
            "adapter_status": adapter_status,
            "user_id": user_id
        })

    async def subscribe_client(self, client_id, data):
        if client_id not in self.user_mapping:
            await self.send_error(client_id, "NOT_AUTHENTICATED", "You must authenticate first")
            return
        symbols = data.get("symbols") or []
        mode_str = data.get("mode", "Quote")
        depth_level = data.get("depth", 5)
        mode_mapping = {"LTP": 1, "Quote": 2, "Depth": 3}
        mode = mode_mapping.get(mode_str, mode_str) if isinstance(mode_str, str) else mode_str
        if not symbols and (data.get("symbol") and data.get("exchange")):
            symbols = [{"symbol": data.get("symbol"), "exchange": data.get("exchange")}]
        if not symbols:
            await self.send_error(client_id, "INVALID_PARAMETERS", "At least one symbol must be specified")
            return
        user_id = self.user_mapping[client_id]
        if user_id not in self.broker_adapters:
            await self.send_error(client_id, "BROKER_ERROR", "Broker adapter not found")
            return
        adapter = self.broker_adapters[user_id]
        broker_name = self.user_broker_mapping.get(user_id, "unknown")
        subscription_responses = []
        subscription_success = True
        for symbol_info in symbols:
            symbol = symbol_info.get("symbol")
            exchange = symbol_info.get("exchange")
            if not symbol or not exchange:
                continue
            response = adapter.subscribe(symbol, exchange, mode, depth_level)
            if response.get("status") == "success":
                subscription_info = {"symbol": symbol, "exchange": exchange, "mode": mode, "depth_level": depth_level, "broker": broker_name}
                if client_id in self.subscriptions:
                    self.subscriptions[client_id].add(json.dumps(subscription_info))
                else:
                    self.subscriptions[client_id] = {json.dumps(subscription_info)}
                subscription_responses.append({"symbol": symbol, "exchange": exchange, "status": "success", "mode": mode_str, "depth": response.get("actual_depth", depth_level), "broker": broker_name})
            else:
                subscription_success = False
                subscription_responses.append({"symbol": symbol, "exchange": exchange, "status": "error", "message": response.get("message", "Subscription failed"), "broker": broker_name})
        await self.send_message(client_id, {"type": "subscribe", "status": "success" if subscription_success else "partial", "subscriptions": subscription_responses, "message": "Subscription processing complete", "broker": broker_name})

    async def unsubscribe_client(self, client_id, data):
        if client_id not in self.user_mapping:
            await self.send_error(client_id, "NOT_AUTHENTICATED", "You must authenticate first")
            return
        is_unsubscribe_all = data.get("type") == "unsubscribe_all" or data.get("action") == "unsubscribe_all"
        symbols = data.get("symbols") or []
        if not symbols and not is_unsubscribe_all and (data.get("symbol") and data.get("exchange")):
            symbols = [{"symbol": data.get("symbol"), "exchange": data.get("exchange"), "mode": data.get("mode", 2)}]
        if not symbols and not is_unsubscribe_all:
            await self.send_error(client_id, "INVALID_PARAMETERS", "Either symbols or unsubscribe_all is required")
            return
        user_id = self.user_mapping[client_id]
        if user_id not in self.broker_adapters:
            await self.send_error(client_id, "BROKER_ERROR", "Broker adapter not found")
            return
        adapter = self.broker_adapters[user_id]
        broker_name = self.user_broker_mapping.get(user_id, "unknown")
        successful_unsubscriptions = []
        failed_unsubscriptions = []
        if is_unsubscribe_all:
            if client_id in self.subscriptions:
                all_subscriptions = [json.loads(sub_json) for sub_json in self.subscriptions[client_id]]
                for sub in all_subscriptions:
                    symbol, exchange, mode = sub.get("symbol"), sub.get("exchange"), sub.get("mode")
                    if symbol and exchange:
                        response = adapter.unsubscribe(symbol, exchange, mode)
                        if response.get("status") == "success":
                            successful_unsubscriptions.append({"symbol": symbol, "exchange": exchange, "status": "success", "broker": broker_name})
                        else:
                            failed_unsubscriptions.append({"symbol": symbol, "exchange": exchange, "status": "error", "message": response.get("message", "Unsubscription failed"), "broker": broker_name})
                self.subscriptions[client_id].clear()
        else:
            for symbol_info in symbols:
                symbol, exchange, mode = symbol_info.get("symbol"), symbol_info.get("exchange"), symbol_info.get("mode", 2)
                if not symbol or not exchange:
                    continue
                response = adapter.unsubscribe(symbol, exchange, mode)
                if response.get("status") == "success":
                    if client_id in self.subscriptions:
                        subscriptions_to_remove = [sub_key for sub_key in self.subscriptions[client_id] if json.loads(sub_key) == {"symbol": symbol, "exchange": exchange, "mode": mode, "broker": broker_name}]
                        for sub_key in subscriptions_to_remove:
                            self.subscriptions[client_id].discard(sub_key)
                    successful_unsubscriptions.append({"symbol": symbol, "exchange": exchange, "status": "success", "broker": broker_name})
                else:
                    failed_unsubscriptions.append({"symbol": symbol, "exchange": exchange, "status": "error", "message": response.get("message", "Unsubscription failed"), "broker": broker_name})
        status = "success"
        if failed_unsubscriptions and successful_unsubscriptions:
            status = "partial"
        elif failed_unsubscriptions and not successful_unsubscriptions:
            status = "error"
        await self.send_message(client_id, {"type": "unsubscribe", "status": status, "message": "Unsubscription processing complete", "successful": successful_unsubscriptions, "failed": failed_unsubscriptions, "broker": broker_name})

    async def send_message(self, client_id, message):
        if client_id in self.clients:
            websocket = self.clients[client_id]
            try:
                await websocket.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                logger.info(f"Connection closed while sending message to client {client_id}")

    async def send_error(self, client_id, code, message):
        await self.send_message(client_id, {"status": "error", "code": code, "message": message})

    async def zmq_listener(self):
        logger.info("Starting ZeroMQ listener")
        while self.running:
            try:
                if not self.running:
                    break
                try:
                    topic, data = await aio.wait_for(self.socket.recv_multipart(), timeout=0.1)
                except aio.TimeoutError:
                    continue
                topic_str = topic.decode('utf-8')
                data_str = data.decode('utf-8')
                market_data = json.loads(data_str)
                parts = topic_str.split('_')
                if len(parts) >= 4 and parts[0] in ["NSE", "BSE"] and parts[1] == "INDEX":
                    broker_name, exchange, symbol, mode_str = "unknown", f"{parts[0]}_{parts[1]}", parts[2], parts[3]
                elif len(parts) >= 5 and parts[1] == "INDEX":
                    broker_name, exchange, symbol, mode_str = parts[0], f"{parts[1]}_{parts[2]}", parts[3], parts[4]
                elif len(parts) >= 4:
                    broker_name, exchange, symbol, mode_str = parts[0], parts[1], parts[2], parts[3]
                elif len(parts) >= 3:
                    broker_name, exchange, symbol, mode_str = "unknown", parts[0], parts[1], parts[2]
                else:
                    logger.warning(f"Invalid topic format: {topic_str}")
                    continue
                mode_map = {"LTP": 1, "QUOTE": 2, "DEPTH": 3}
                mode = mode_map.get(mode_str)
                if not mode:
                    logger.warning(f"Invalid mode in topic: {mode_str}")
                    continue
                subscriptions_snapshot = list(self.subscriptions.items())
                for client_id, subscriptions in subscriptions_snapshot:
                    user_id = self.user_mapping.get(client_id)
                    if not user_id:
                        continue
                    client_broker = self.user_broker_mapping.get(user_id)
                    if broker_name != "unknown" and client_broker and client_broker != broker_name:
                        continue
                    subscriptions_list = list(subscriptions)
                    for sub_json in subscriptions_list:
                        try:
                            sub = json.loads(sub_json)
                            if (sub.get("symbol") == symbol and sub.get("exchange") == exchange and sub.get("mode") == mode):
                                await self.send_message(client_id, {"type": "market_data", "symbol": symbol, "exchange": exchange, "mode": mode, "broker": broker_name if broker_name != "unknown" else client_broker, "data": market_data})
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing subscription: {sub_json}, Error: {e}")
                            continue
            except Exception as e:
                logger.error(f"Error in ZeroMQ listener: {e}")
                await aio.sleep(1)


async def main():
    proxy = None
    try:
        ws_host = settings.WEBSOCKET_HOST
        ws_port = settings.WEBSOCKET_PORT
        proxy = WebSocketProxy(host=ws_host, port=ws_port)
        await proxy.start()
    except KeyboardInterrupt:
        logger.info("Server stopped by user (KeyboardInterrupt)")
    except RuntimeError as e:
        if "set_wakeup_fd only works in main thread" in str(e):
            logger.error(f"Error in start method: {e}")
            logger.info("Starting ZeroMQ listener without signal handlers")
            if proxy:
                await proxy.zmq_listener()
        else:
            logger.error(f"Runtime error: {e}")
            raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Server error: {e}\n{error_details}")
        raise
    finally:
        if proxy:
            try:
                await proxy.stop()
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup: {cleanup_error}")


if __name__ == "__main__":
    aio.run(main())
