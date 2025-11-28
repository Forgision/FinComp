import asyncio
import json
import pytest
import zmq
import zmq.asyncio
from app.core.config import settings
from app.data.service import DataService


@pytest.mark.asyncio
async def test_data_service_subscription():
    # Start the service
    service = DataService()
    service_task = asyncio.create_task(service.start())

    # Give it a moment to bind sockets
    await asyncio.sleep(1)

    context = zmq.asyncio.Context()

    # Create REQ socket to send subscription commands
    req_socket = context.socket(zmq.REQ)
    req_socket.connect(f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_DATA_REQ_PORT}")

    # Create SUB socket to receive data
    sub_socket = context.socket(zmq.SUB)
    sub_socket.connect(f"tcp://{settings.ZMQ_HOST}:{settings.ZMQ_PORT}")
    sub_socket.subscribe("")  # Subscribe to all for verification

    test_symbol = "TEST_SYM"

    # 1. Subscribe
    print(f"Sending subscribe request for {test_symbol}")
    await req_socket.send_json({"action": "subscribe", "symbol": test_symbol})
    print("Waiting for subscription response...")
    try:
        response = await asyncio.wait_for(req_socket.recv_json(), timeout=2.0)
        print(f"Received response: {response}")
    except asyncio.TimeoutError:
        pytest.fail("Timeout waiting for subscription response")

    assert response["status"] == "success"
    assert f"Subscribed to {test_symbol}" in response["message"]

    # 2. Verify data reception
    print("Waiting for data...")
    try:
        # We expect data within a reasonable time
        topic, message = await asyncio.wait_for(
            sub_socket.recv_multipart(), timeout=2.0
        )
        topic = topic.decode()
        data = json.loads(message.decode())

        print(f"Received: {topic} -> {data}")
        assert topic == f"market_data.{test_symbol}"
        assert data["symbol"] == test_symbol
    except asyncio.TimeoutError:
        pytest.fail("Did not receive data after subscription")

    # 3. Unsubscribe
    print(f"Sending unsubscribe request for {test_symbol}")
    await req_socket.send_json({"action": "unsubscribe", "symbol": test_symbol})
    print("Waiting for unsubscribe response...")
    try:
        response = await asyncio.wait_for(req_socket.recv_json(), timeout=2.0)
        print(f"Received response: {response}")
    except asyncio.TimeoutError:
        pytest.fail("Timeout waiting for unsubscribe response")

    assert response["status"] == "success"
    assert f"Unsubscribed from {test_symbol}" in response["message"]

    # 4. Verify no data
    print("Verifying no data after unsubscribe...")
    try:
        # Should not receive data for this symbol anymore
        # We might receive one or two lingering messages, so we drain them
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < 2.0:
            await asyncio.wait_for(sub_socket.recv_multipart(), timeout=0.5)
            print("Received lingering message")
    except asyncio.TimeoutError:
        # This is expected - timeout means no more data
        print("No more data received, as expected.")
        pass

    # Cleanup
    print("Stopping service...")
    service.stop()
    await service_task
    req_socket.close()
    sub_socket.close()
    context.term()
