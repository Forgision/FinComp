import pytest
import sys
from unittest.mock import MagicMock

# Mock socketio
mock_socketio = MagicMock()
sys.modules["socketio"] = mock_socketio
sys.modules["app.utils.web.socketio"] = MagicMock()

# Mock slowapi
mock_slowapi = MagicMock()
sys.modules["slowapi"] = mock_slowapi
sys.modules["slowapi.errors"] = MagicMock()
sys.modules["slowapi.extension"] = MagicMock()
sys.modules["slowapi.util"] = MagicMock()
sys.modules["slowapi.middleware"] = MagicMock()

from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.web.backend.api.dummy_api import dummy_router

# Create a standalone app for testing the dummy router
# This avoids importing the main app which has many dependencies that might be missing in the test env
app = FastAPI()
app.include_router(dummy_router, prefix="/api/dummy")

client = TestClient(app)


def test_get_market_summary():
    response = client.get("/api/dummy/market-summary")
    assert response.status_code == 200
    data = response.json()
    assert "indices" in data
    assert "advancers" in data
    assert "decliners" in data
    assert len(data["indices"]) > 0


def test_get_orders():
    response = client.get("/api/dummy/orders")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "order_id" in data[0]
        assert "symbol" in data[0]


def test_get_positions():
    response = client.get("/api/dummy/positions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "symbol" in data[0]
        assert "pnl" in data[0]


def test_get_holdings():
    response = client.get("/api/dummy/holdings")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "symbol" in data[0]
        assert "quantity" in data[0]


def test_get_strategies():
    response = client.get("/api/dummy/strategies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "strategy_id" in data[0]
        assert "status" in data[0]
