import json
import time
import zmq
import pytest
from app.data.service import get_data_service
from app.core.config import settings


@pytest.mark.asyncio
async def test_zmq_integration():
    """
    Test that MarketDataService correctly receives data published to ZMQ.
    """
    # 1. Get the service instance (this starts the ZMQ listener thread)
    await get_data_service(mode="CLIENT").reset_instance()
    service = get_data_service(mode="CLIENT")

    # Allow some time for the subscriber to connect
    time.sleep(1)

    # 2. Create a ZMQ Publisher (simulating a Broker Adapter)
    context = zmq.Context()
    pub_socket = context.socket(zmq.PUB)
    zmq_url = f"tcp://*:{settings.ZMQ_PORT}"

    try:
        try:
            pub_socket.bind(zmq_url)
        except zmq.ZMQError:
            # If bind fails, it might be because the service or another test is using it.
            # Ideally, we should use a dynamic port for testing, but for this integration test
            # we are testing against the configured port.
            # If it fails, we might need to rethink the test strategy or config.
            pytest.skip("Could not bind to ZMQ port. It might be in use.")

        # Allow some time for the subscription to be established
        time.sleep(1)

        # 3. Publish a mock market data tick
        test_symbol = "TEST_ZMQ"
        test_exchange = "NSE"
        test_ltp = 123.45

        payload = {
            "symbol": test_symbol,
            "exchange": test_exchange,
            "mode": 1,  # LTP
            "data": {"ltp": test_ltp, "timestamp": int(time.time())},
        }

        topic = f"{test_exchange}:{test_symbol}"

        # Publish multiple times to ensure delivery (PUB/SUB slow joiner syndrome)
        for _ in range(5):
            pub_socket.send_multipart(
                [topic.encode("utf-8"), json.dumps(payload).encode("utf-8")]
            )
            time.sleep(0.1)

        # 4. Verify that MarketDataService received and processed the data
        # We poll the service cache

        max_retries = 10
        found = False

        for _ in range(max_retries):
            ltp_data = service.get_ltp(test_symbol, test_exchange)
            if ltp_data and ltp_data.get("value") == test_ltp:
                found = True
                break
            time.sleep(0.2)

        assert found, f"MarketDataService did not update LTP for {test_symbol} via ZMQ"

    finally:
        # Cleanup
        pub_socket.close()
        context.term()
        await service.stop()
        await service.reset_instance()
