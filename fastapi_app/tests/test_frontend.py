import pytest
from httpx import AsyncClient
from fastapi import FastAPI

@pytest.mark.asyncio
async def test_get_websocket_dashboard(async_client: AsyncClient):
    """
    Test the /websocket/dashboard endpoint.
    """
    response = await async_client.get("/api/v1/websocket/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "WebSocket Dashboard" in response.text

@pytest.mark.asyncio
async def test_get_websocket_test(async_client: AsyncClient):
    """
    Test the /websocket/test endpoint.
    """
    response = await async_client.get("/api/v1/websocket/test")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "WebSocket Test" in response.text