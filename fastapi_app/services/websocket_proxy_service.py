import asyncio
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState
from typing import Dict, Set, Tuple, Union, Any, Optional, Callable
from collections import defaultdict
from fastapi import status

from fastapi_app.core.config import settings
from fastapi_app.core.logging import get_logger

logger = get_logger("websocket_proxy")

class WebSocketProxyService:
    def __init__(self, auth_dependency: Callable):
        self.auth_dependency = auth_dependency
        self.clients: Dict[str, WebSocket] = {} # user_id -> websocket
        self.subscriptions: Dict[str, Set[str]] = {} # user_id -> set of subscriptions
        self.broker_adapters: Dict[str, Any] = {} # user_id -> broker_adapter instance
        self.user_mapping: Dict[WebSocket, str] = {} # websocket -> user_id
        self.user_broker_mapping: Dict[str, str] = {} # user_id -> broker_name
        self.subscription_index: Dict[Tuple[str, str, int], Set[str]] = defaultdict(set) # (symbol, exchange, mode) -> set of user_ids
        self.last_message_time: Dict[Tuple[str, str, int], float] = {} # (symbol, exchange, mode) -> last send time
        self.message_throttle_interval = 0.05
        self.MODE_MAP = {"LTP": 1, "QUOTE": 2, "DEPTH": 3}

    async def handle_fastapi_websocket(self, websocket: WebSocket):
        await websocket.accept()
        logger.info(f"Client connected: {websocket.client}")
        user_id: Optional[str] = None
        try:
            # First message must be an authentication message
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"Client {websocket.client} did not send authentication in time.")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication timeout")
                return

            action = data.get("action") or data.get("type")

            if action in ["authenticate", "auth"]:
                user_id = await self.authenticate_client(websocket, data)
                if user_id:
                    self.clients[user_id] = websocket
                    self.subscriptions[user_id] = set()
                    self.user_mapping[websocket] = user_id
                    logger.info(f"Client {user_id} authenticated and connected.")
                    await websocket.send_json({
                        "type": "auth_status",
                        "status": "success",
                        "message": "Authenticated successfully"
                    })
                else:
                    logger.warning(f"Client {websocket.client} authentication failed.")
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
                    return
            else:
                logger.warning(f"Client {websocket.client} sent non-auth message first.")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
                return

            # Now that the client is authenticated, process further messages in a loop
            while True:
                message = await websocket.receive_text()
                try:
                    await self.process_client_message(user_id, message)
                except Exception as e:
                    logger.exception(f"Error processing message from client {user_id}: {e}")
                    await self.send_error(user_id, "PROCESSING_ERROR", str(e))

        except WebSocketDisconnect as e:
            logger.info(f"Client disconnected: {user_id or websocket.client}, code: {e.code}, reason: {e.reason}")
        except json.JSONDecodeError:
            logger.warning(f"Client {websocket.client} sent invalid JSON.")
            # Starlette handles closing the connection on JSON errors
        except Exception as e:
            logger.exception(f"Unexpected error handling client {user_id or websocket.client}: {e}")
        finally:
            if user_id:
                await self.cleanup_client(user_id)
            else:
                logger.info(f"Unauthenticated client {websocket.client} disconnected.")

    async def process_client_message(self, user_id: str, message: str):
        try:
            data = json.loads(message)
            action = data.get("action") or data.get("type")

            if action not in ["subscribe", "unsubscribe"]:
                logger.info(f"Client {user_id} requested action: {action}")

            if action in ["authenticate", "auth"]:
                # Authentication should only happen once, but we can handle re-auth if needed
                pass
            elif action == "subscribe":
                await self.subscribe_client(user_id, data)
            elif action in ["unsubscribe", "unsubscribe_all"]:
                await self.unsubscribe_client(user_id, data)
            elif action == "get_broker_info":
                await self.get_broker_info(user_id)
            elif action == "get_supported_brokers":
                await self.get_supported_brokers(user_id)
            else:
                logger.warning(f"Client {user_id} requested invalid action: {action}")
                await self.send_error(user_id, "INVALID_ACTION", f"Invalid action: {action}")
        except json.JSONDecodeError as e:
            logger.exception(f"Invalid JSON from client {user_id}: {message}")
            await self.send_error(user_id, "INVALID_JSON", "Invalid JSON message")
        except Exception as e:
            logger.exception(f"Error processing client message: {e}")
            await self.send_error(user_id, "SERVER_ERROR", str(e))

    async def authenticate_client(self, websocket: WebSocket, data: Dict[str, str]) -> Optional[str]:
        api_key = data.get("api_key")
        logger.info(f"api_key: {api_key}")
        if not api_key:
            await self.send_error(websocket, "AUTHENTICATION_ERROR", "API key is required")
            return None

        try:
            # Verify the API key and get the auth data using the injected dependency
            auth_data = await self.auth_dependency(api_key)
            logger.info(f"auth_data: {auth_data}")
            if not auth_data:
                await self.send_error(websocket, "AUTHENTICATION_ERROR", "Invalid API key")
                return None
        except Exception as e:
            logger.error(f"API key verification failed for client {websocket.client}: {e}")
            await self.send_error(websocket, "AUTHENTICATION_ERROR", "API key verification failed")
            return None

        user_id = auth_data.token

        # Store the broker mapping for this user
        self.user_broker_mapping[user_id] = auth_data.broker
        return user_id

    async def get_supported_brokers(self, user_id: str):
        try:
            valid_brokers = os.getenv('VALID_BROKERS', '').split(',')
            supported_brokers = [broker.strip() for broker in valid_brokers if broker.strip()]

            await self.send_message(user_id, {
                "type": "supported_brokers",
                "status": "success",
                "brokers": supported_brokers,
                "count": len(supported_brokers)
            })
        except Exception as e:
            logger.error(f"Error getting supported brokers: {e}")
            await self.send_error(user_id, "BROKER_LIST_ERROR", str(e))

    async def get_broker_info(self, user_id: str):
        if user_id not in self.clients:
            await self.send_error(user_id, "NOT_AUTHENTICATED", "You must be connected and authenticated")
            return

        broker_name = self.user_broker_mapping.get(user_id)

        if not broker_name:
            await self.send_error(user_id, "BROKER_ERROR", "Broker information not available for this user")
            return

        # Get adapter status
        adapter_status = "disconnected"
        if user_id in self.broker_adapters:
            adapter = self.broker_adapters[user_id]
            adapter_status = getattr(adapter, 'status', 'connected')

        await self.send_message(user_id, {
            "type": "broker_info",
            "status": "success",
            "broker": broker_name,
            "adapter_status": adapter_status,
            "user_id": user_id
        })

    async def subscribe_client(self, user_id: str, data: Dict[str, any]):
        if user_id not in self.clients:
            await self.send_error(user_id, "NOT_AUTHENTICATED", "You must be connected and authenticated")
            return

        symbols = data.get("symbols", [])
        mode_str = data.get("mode", "Quote")
        depth_level = data.get("depth", 5)

        mode = self.MODE_MAP.get(mode_str.upper(), 2)

        if not symbols and (data.get("symbol") and data.get("exchange")):
            symbols = [{"symbol": data.get("symbol"), "exchange": data.get("exchange")}]

        if not symbols:
            await self.send_error(user_id, "INVALID_PARAMETERS", "At least one symbol must be specified")
            return

        if user_id not in self.broker_adapters:
            await self.send_error(user_id, "BROKER_ERROR", "Broker adapter not found for this user")
            return

        adapter = self.broker_adapters[user_id]
        broker_name = self.user_broker_mapping.get(user_id, "unknown")

        subscription_responses = []
        subscription_success = True

        for symbol_info in symbols:
            symbol, exchange = symbol_info.get("symbol"), symbol_info.get("exchange")
            if not symbol or not exchange:
                continue

            response = adapter.subscribe(symbol, exchange, mode, depth_level)
            subscription_info = {
                "symbol": symbol, "exchange": exchange, "mode": mode,
                "depth_level": depth_level, "broker": broker_name
            }

            if response.get("status") == "success":
                self.subscriptions.setdefault(user_id, set()).add(json.dumps(subscription_info))
                sub_key = (symbol, exchange, mode)
                self.subscription_index[sub_key].add(user_id)
                subscription_responses.append({
                    "symbol": symbol, "exchange": exchange, "status": "success", "mode": mode_str,
                    "depth": response.get("actual_depth", depth_level), "broker": broker_name
                })
            else:
                subscription_success = False
                subscription_responses.append({
                    "symbol": symbol, "exchange": exchange, "status": "error",
                    "message": response.get("message", "Subscription failed"), "broker": broker_name
                })

        await self.send_message(user_id, {
            "type": "subscribe", "status": "success" if subscription_success else "partial",
            "subscriptions": subscription_responses, "message": "Subscription processing complete",
            "broker": broker_name
        })

    async def unsubscribe_client(self, user_id: str, data: Dict[str, any]):
        if user_id not in self.clients:
            await self.send_error(user_id, "NOT_AUTHENTICATED", "You must be connected and authenticated")
            return

        is_unsubscribe_all = data.get("type") == "unsubscribe_all" or data.get("action") == "unsubscribe_all"
        symbols = data.get("symbols", [])

        if not symbols and not is_unsubscribe_all and (data.get("symbol") and data.get("exchange")):
            symbols = [{"symbol": data.get("symbol"), "exchange": data.get("exchange"), "mode": data.get("mode", "Quote")}]

        if not symbols and not is_unsubscribe_all:
            await self.send_error(user_id, "INVALID_PARAMETERS", "Either symbols or unsubscribe_all is required")
            return

        if user_id not in self.broker_adapters:
            await self.send_error(user_id, "BROKER_ERROR", "Broker adapter not found for this user")
            return

        adapter = self.broker_adapters[user_id]
        broker_name = self.user_broker_mapping.get(user_id, "unknown")
        successful_unsubscriptions, failed_unsubscriptions = [], []

        if is_unsubscribe_all:
            if user_id in self.subscriptions:
                for sub_json in list(self.subscriptions[user_id]): # Iterate over a copy
                    try:
                        sub = json.loads(sub_json)
                        response = adapter.unsubscribe(sub["symbol"], sub["exchange"], sub["mode"])
                        if response.get("status") == "success":
                            successful_unsubscriptions.append({"symbol": sub["symbol"], "exchange": sub["exchange"], "status": "success"})
                            self.subscriptions[user_id].discard(sub_json)
                        else:
                            failed_unsubscriptions.append({"symbol": sub["symbol"], "exchange": sub["exchange"], "status": "error", "message": response.get("message")})
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.error(f"Error unsubscribing from {sub_json}: {e}")
                self.subscriptions[user_id].clear()
        else:
            for symbol_info in symbols:
                symbol, exchange = symbol_info.get("symbol"), symbol_info.get("exchange")
                mode_str = symbol_info.get("mode", "Quote")
                mode = self.MODE_MAP.get(mode_str.upper(), 2)
                if not symbol or not exchange:
                    continue
                response = adapter.unsubscribe(symbol, exchange, mode)
                if response.get("status") == "success":
                    successful_unsubscriptions.append({"symbol": symbol, "exchange": exchange, "status": "success"})
                    # Remove the specific subscription
                    if user_id in self.subscriptions:
                        for sub_json in list(self.subscriptions[user_id]):
                            sub = json.loads(sub_json)
                            if sub["symbol"] == symbol and sub["exchange"] == exchange and sub["mode"] == mode:
                                self.subscriptions[user_id].discard(sub_json)
                else:
                    failed_unsubscriptions.append({"symbol": symbol, "exchange": exchange, "status": "error", "message": response.get("message")})

        status = "success"
        if failed_unsubscriptions and successful_unsubscriptions: status = "partial"
        elif failed_unsubscriptions and not successful_unsubscriptions: status = "error"

        await self.send_message(user_id, {
            "type": "unsubscribe", "status": status, "message": "Unsubscription processing complete",
            "successful": successful_unsubscriptions, "failed": failed_unsubscriptions, "broker": broker_name
        })

    async def send_message(self, user_id: str, message: Dict[str, any]):
        if user_id in self.clients:
            websocket = self.clients[user_id]
            try:
                await websocket.send_json(message)
            except WebSocketDisconnect:
                logger.warning(f"Connection to client {user_id} was closed. Could not send message.")
                # The cleanup will be handled by the main handle_client loop

    async def send_error(self, recipient: Union[str, WebSocket], code: str, message: str):
        error_message = {"status": "error", "code": code, "message": message}
        if isinstance(recipient, str): # It's a user_id
            await self.send_message(recipient, error_message)
        else: # It's a websocket connection
            try:
                await recipient.send_json(error_message)
            except WebSocketDisconnect:
                logger.warning(f"Connection to unauthenticated client {recipient.client} was closed.")

    async def cleanup_client(self, user_id: str):
        logger.info(f"Cleaning up resources for client {user_id}")
        websocket = self.clients.pop(user_id, None)
        if websocket:
            self.user_mapping.pop(websocket, None)

        self.subscriptions.pop(user_id, None)
        self.broker_adapters.pop(user_id, None)
        self.user_broker_mapping.pop(user_id, None)

        # Remove from subscription index
        keys_to_remove_from = []
        for key, users in self.subscription_index.items():
            if user_id in users:
                users.discard(user_id)
                if not users:
                    keys_to_remove_from.append(key)

        for key in keys_to_remove_from:
            self.subscription_index.pop(key, None)

        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=status.WS_1000_NORMAL_CLOSURE, reason="Server initiated cleanup")





