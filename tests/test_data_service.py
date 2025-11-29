import pytest
import asyncio
import zmq
import zmq.asyncio
import json
from app.data.service import DataService
from app.core.config import settings


@pytest.mark.asyncio
class TestDataService:
    @pytest.fixture(autouse=True)
    async def setup_service(self):
        self.service = DataService()
        self.start_task = asyncio.create_task(self.service.start())
        # Give it a moment to start
        await asyncio.sleep(0.5)
        yield
        await self.service.stop()
        await self.start_task
        # Give it a moment to cleanup
        await asyncio.sleep(0.2)

    @pytest.fixture
    def zmq_context(self):
        context = zmq.asyncio.Context()
        yield context
        context.term()

    async def test_service_initialization(self):
        assert self.service.running is True
        assert self.service.broker_manager.is_dummy is True

    async def test_authorize(self, zmq_context):
        req_socket = zmq_context.socket(zmq.REQ)
        req_socket.connect(f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_DATA_REQ_PORT}")

        await req_socket.send_json(
            {
                "action": "authorize",
                "broker_id": "dummy",
                "auth_data": {},
                "mode": "fallback",
            }
        )

        response = await asyncio.wait_for(req_socket.recv_json(), timeout=2.0)
        assert response["status"] == "success"
        assert "Authorized dummy" in response["message"]

        req_socket.close()

    async def test_subscribe_unsubscribe_flow(self, zmq_context):
        req_socket = zmq_context.socket(zmq.REQ)
        req_socket.connect(f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_DATA_REQ_PORT}")

        sub_socket = zmq_context.socket(zmq.SUB)
        sub_socket.connect(f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_PORT}")
        sub_socket.subscribe("")

        symbol = "TEST_SYM"

        # Subscribe
        await req_socket.send_json({"action": "subscribe", "symbol": symbol})
        response = await asyncio.wait_for(req_socket.recv_json(), timeout=2.0)
        assert response["status"] == "success"

        # Verify data
        try:
            topic, message = await asyncio.wait_for(
                sub_socket.recv_multipart(), timeout=3.0
            )
            data = json.loads(message.decode())
            assert data["symbol"] == symbol
        except asyncio.TimeoutError:
            pytest.fail("Did not receive data after subscription")

        # Unsubscribe
        await req_socket.send_json({"action": "unsubscribe", "symbol": symbol})
        response = await asyncio.wait_for(req_socket.recv_json(), timeout=2.0)
        assert response["status"] == "success"

        req_socket.close()
        sub_socket.close()

    async def test_handle_history_requests(self, zmq_context):
        dealer_socket = zmq_context.socket(zmq.DEALER)
        dealer_socket.connect(
            f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_DATA_ROUTER_PORT}"
        )

        # Send history request
        # Router expects [identity, empty, message]
        # Dealer sends [empty, message] (identity is handled by ZMQ)
        # Wait, if I use DEALER, I just send the message. ZMQ adds the identity frame when it reaches Router.
        # But Router expects [identity, empty, message].
        # So Dealer should send [empty, message].
        # Let's verify what Router expects:
        # msg = await self.router_socket.recv_multipart()
        # identity = msg[0]
        # msg[1] is empty delimiter
        # _payload = json.loads(msg[2].decode())

        # So Dealer should send [b"", json_payload]

        await dealer_socket.send_multipart(
            [b"", json.dumps({"action": "history"}).encode()]
        )

        # Receive response
        msg = await asyncio.wait_for(dealer_socket.recv_multipart(), timeout=2.0)
        # msg[0] should be empty delimiter
        payload = json.loads(msg[1].decode())

        assert payload["status"] == "error"
        assert "History not implemented yet" in payload["message"]

        dealer_socket.close()
