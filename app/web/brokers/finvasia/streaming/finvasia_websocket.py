import websocket
import json
import threading
import time
from typing import Any, Callable, Dict, Optional


from app.utils.logging import logger


class FinvasiaWebSocket:
    """
    NOTE: This is a placeholder implementation.
    """

    WS_URL = "wss://api.finvasia.com/NorenWSTP/"
    CONNECTION_TIMEOUT = 15
    THREAD_JOIN_TIMEOUT = 5
    HEARTBEAT_INTERVAL = 30
    HEARTBEAT_TIMEOUT = 120
    PING_INTERVAL = 30
    PING_TIMEOUT = 10
    MSG_TYPE_CONNECT = "c"
    MSG_TYPE_HEARTBEAT = "h"
    MSG_TYPE_AUTH_ACK = "ck"
    MSG_TYPE_TOUCHLINE_SUB = "t"
    MSG_TYPE_TOUCHLINE_UNSUB = "u"
    MSG_TYPE_DEPTH_SUB = "d"
    MSG_TYPE_DEPTH_UNSUB = "ud"
    AUTH_SUCCESS = "OK"

    def __init__(
        self,
        user_id: str,
        actid: str,
        susertoken: str,
        on_message: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        on_close: Optional[Callable] = None,
        on_open: Optional[Callable] = None,
    ):
        self.user_id = user_id
        self.actid = actid
        self.susertoken = susertoken
        self.ws = None
        self.ws_thread = None
        self.running = False
        self.connected = False
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.on_open = on_open
        self._heartbeat_thread = None
        self._last_message_time = None
        self._heartbeat_lock = threading.Lock()
        self.logger = logger

    def connect(self) -> bool:
        if self.running:
            self.logger.warning("Already connected or connecting")
            return True
        try:
            self._initialize_connection()
            return self._wait_for_connection()
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            self.stop()
            return False

    def _initialize_connection(self) -> None:
        self.running = True
        self.ws = websocket.WebSocketApp(
            self.WS_URL,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
        self.ws_thread.start()

    def _wait_for_connection(self) -> bool:
        start_time = time.time()
        while time.time() - start_time < self.CONNECTION_TIMEOUT:
            if self.connected:
                self.logger.info("WebSocket connected successfully")
                return True
            time.sleep(0.1)
        self.logger.error("Connection timeout")
        self.stop()
        return False

    def _run_websocket(self) -> None:
        try:
            self.ws.run_forever(
                ping_interval=self.PING_INTERVAL, ping_timeout=self.PING_TIMEOUT
            )
        except Exception as e:
            self.logger.error(f"WebSocket run error: {e}")
        finally:
            self._cleanup_connection_state()

    def _cleanup_connection_state(self) -> None:
        self.connected = False
        self._stop_heartbeat()

    def stop(self) -> None:
        self.logger.info("Stopping WebSocket connection")
        self.running = False
        self.connected = False
        self._close_websocket()
        self._wait_for_thread_completion()
        self._stop_heartbeat()

    def _close_websocket(self) -> None:
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                self.logger.error(f"Error closing WebSocket: {e}")

    def _wait_for_thread_completion(self) -> None:
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=self.THREAD_JOIN_TIMEOUT)
            if self.ws_thread.is_alive():
                self.logger.warning("WebSocket thread did not terminate within timeout")

    def _on_open(self, ws) -> None:
        self.connected = True
        self._update_last_message_time()
        self.logger.info("WebSocket connection opened, sending authentication")
        if self._send_authentication():
            self._start_heartbeat()
            self._call_external_callback(self.on_open, ws)

    def _send_authentication(self) -> bool:
        auth_msg = {
            "t": self.MSG_TYPE_CONNECT,
            "uid": self.user_id,
            "actid": self.actid,
            "source": "API",
            "susertoken": self.susertoken,
        }
        try:
            self.ws.send(json.dumps(auth_msg))
            self.logger.info("Authentication message sent")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send authentication: {e}")
            return False

    def _on_message(self, ws, message: str) -> None:
        self._update_last_message_time()
        if self._handle_internal_message(message):
            return
        self._call_external_callback(self.on_message, ws, message)

    def _handle_internal_message(self, message: str) -> bool:
        try:
            data = json.loads(message)
            msg_type = data.get("t")
            if msg_type == self.MSG_TYPE_AUTH_ACK:
                return self._handle_auth_response(data)
            elif msg_type == self.MSG_TYPE_HEARTBEAT:
                self.logger.debug("Received heartbeat response")
                return True
        except (json.JSONDecodeError, KeyError):
            pass
        return False

    def _handle_auth_response(self, data: Dict[str, Any]) -> bool:
        if data.get("s") == self.AUTH_SUCCESS:
            self.logger.info("Authentication successful")
        else:
            self.logger.error(f"Authentication failed: {data}")
        return True

    def _on_error(self, ws, error) -> None:
        self.logger.error(f"WebSocket error: {error}")
        self._call_external_callback(self.on_error, ws, error)

    def _on_close(
        self, ws, close_status_code: Optional[int], close_msg: Optional[str]
    ) -> None:
        self.connected = False
        self.logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")
        self._stop_heartbeat()
        self._call_external_callback(self.on_close, ws, close_status_code, close_msg)

    def _call_external_callback(self, callback: Optional[Callable], *args) -> None:
        if callback:
            try:
                callback(*args)
            except Exception as e:
                self.logger.error(f"Error in external callback: {e}")

    def _update_last_message_time(self) -> None:
        with self._heartbeat_lock:
            self._last_message_time = time.time()

    def _start_heartbeat(self) -> None:
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_worker, daemon=True
        )
        self._heartbeat_thread.start()
        self.logger.debug("Heartbeat thread started")

    def _stop_heartbeat(self) -> None:
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self.logger.debug("Waiting for heartbeat thread to stop")

    def _heartbeat_worker(self) -> None:
        while self.running and self.connected:
            try:
                time.sleep(self.HEARTBEAT_INTERVAL)
                if self.running and self.connected:
                    if not self._send_heartbeat():
                        break
                    if not self._check_connection_health():
                        break
            except Exception as e:
                self.logger.error(f"Heartbeat worker error: {e}")
                break

    def _send_heartbeat(self) -> bool:
        if not self.ws:
            return False
        try:
            heartbeat_msg = {"t": self.MSG_TYPE_HEARTBEAT}
            self.ws.send(json.dumps(heartbeat_msg))
            self.logger.debug("Sent heartbeat")
            return True
        except Exception as e:
            self.logger.error(f"Heartbeat send error: {e}")
            return False

    def _check_connection_health(self) -> bool:
        with self._heartbeat_lock:
            if self._last_message_time:
                time_since_message = time.time() - self._last_message_time
                if time_since_message > self.HEARTBEAT_TIMEOUT:
                    self.logger.error("Connection timeout - no messages received")
                    self._close_websocket()
                    return False
        return True

    def subscribe_touchline(self, scrip_list: str) -> bool:
        return self._send_subscription_message(
            self.MSG_TYPE_TOUCHLINE_SUB, scrip_list, "touchline subscription"
        )

    def unsubscribe_touchline(self, scrip_list: str) -> bool:
        return self._send_subscription_message(
            self.MSG_TYPE_TOUCHLINE_UNSUB, scrip_list, "touchline unsubscription"
        )

    def subscribe_depth(self, scrip_list: str) -> bool:
        return self._send_subscription_message(
            self.MSG_TYPE_DEPTH_SUB, scrip_list, "depth subscription"
        )

    def unsubscribe_depth(self, scrip_list: str) -> bool:
        return self._send_subscription_message(
            self.MSG_TYPE_DEPTH_UNSUB, scrip_list, "depth unsubscription"
        )

    def _send_subscription_message(
        self, msg_type: str, scrip_list: str, operation_name: str
    ) -> bool:
        message_dict = {"t": msg_type, "k": scrip_list}
        return self._send_message(message_dict, operation_name)

    def _send_message(self, message_dict: Dict[str, Any], operation_name: str) -> bool:
        if not self._validate_connection_state(operation_name):
            return False
        try:
            message_json = json.dumps(message_dict)
            self.ws.send(message_json)
            self.logger.debug(f"Sent {operation_name}: {message_dict}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send {operation_name}: {e}")
            return False

    def _validate_connection_state(self, operation_name: str) -> bool:
        if not self.ws:
            self.logger.warning(
                f"Cannot send {operation_name}: WebSocket not initialized"
            )
            return False
        if not self.connected:
            self.logger.warning(f"Cannot send {operation_name}: not connected")
            return False
        return True

    def is_connected(self) -> bool:
        return self.connected and self.running

    def get_connection_info(self) -> Dict[str, Any]:
        return {
            "connected": self.connected,
            "running": self.running,
            "user_id": self.user_id,
            "actid": self.actid,
            "ws_url": self.WS_URL,
            "last_message_time": self._last_message_time,
            "heartbeat_thread_alive": self._heartbeat_thread.is_alive()
            if self._heartbeat_thread
            else False,
            "ws_thread_alive": self.ws_thread.is_alive() if self.ws_thread else False,
        }
