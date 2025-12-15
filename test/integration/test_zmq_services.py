import pytest
import zmq
import zmq.asyncio
from app.core.config import settings
from app.web.websocket.fastapi_integration import (
    start_data_service,
    start_algo_service,
    start_execution_service,
    cleanup_data_service,
    cleanup_algo_service,
    cleanup_execution_service,
)
import asyncio

@pytest.mark.asyncio
async def test_services_startup_and_bind():
    # Start services
    start_data_service()
    start_algo_service()
    start_execution_service()

    await asyncio.sleep(2) # Allow bind

    context = zmq.asyncio.Context()

    ports = [
        settings.ZMQ_PORT,
        settings.ZMQ_DATA_REQ_PORT,
        settings.ZMQ_DATA_ROUTER_PORT,
        settings.ZMQ_ALGO_PUB_PORT,
        settings.ZMQ_EXECUTION_PUB_PORT,
        settings.ZMQ_EXECUTION_ROUTER_PORT,
    ]

    for port in ports:
        socket = context.socket(zmq.SUB)
        # Try to connect
        try:
            socket.connect(f"tcp://{settings.ZMQ_HOST}:{port}")
        except Exception as e:
            pytest.fail(f"Failed to connect to port {port}: {e}")
        finally:
            socket.close()

    # Cleanup
    cleanup_data_service()
    cleanup_algo_service()
    cleanup_execution_service()
    context.term()
