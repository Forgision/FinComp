import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.brokers.upstox import UpstoxAuth, UpstoxAccount, UpstoxData
from app.core.brokers.base import AuthConfig


@pytest.mark.asyncio
async def test_upstox_auth_instantiation():
    auth = UpstoxAuth()
    assert isinstance(auth, UpstoxAuth)


@pytest.mark.asyncio
async def test_upstox_auth_authenticate():
    auth = UpstoxAuth()
    config = AuthConfig(auth_code="test_code")

    with patch(
        "app.core.brokers.upstox.upstox_auth.get_httpx_client"
    ) as mock_get_client:
        mock_client = MagicMock()
        mock_post = AsyncMock()
        mock_client.post = mock_post
        mock_get_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "token123"}
        mock_post.return_value = mock_response

        token = await auth.authenticate(config)
        assert token == "token123"


@pytest.mark.asyncio
async def test_upstox_account_instantiation():
    account = UpstoxAccount()
    assert isinstance(account, UpstoxAccount)


@pytest.mark.asyncio
async def test_upstox_account_place_order():
    account = UpstoxAccount()
    order_data = {
        "symbol": "NSE:SBIN-EQ",
        "quantity": 1,
        "pricetype": "MARKET",
        "action": "BUY",
        "product": "MIS",
        "exchange": "NSE",
    }

    with (
        patch(
            "app.core.brokers.upstox.upstox_account.get_httpx_client"
        ) as mock_get_client,
        patch(
            "app.core.brokers.upstox.upstox_account.get_token", new_callable=AsyncMock
        ) as mock_get_token,
    ):
        mock_get_token.return_value = "12345"

        mock_client = MagicMock()
        mock_post = AsyncMock()
        mock_client.post = mock_post
        mock_get_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"order_id": "order123"},
        }
        mock_post.return_value = mock_response

        response = await account.place_order(order_data, "auth_token")

        if response.get("status") != "success":
            pytest.fail(f"Upstox place_order failed: {response.get('message')}")

        assert response["status"] == "success"
        assert response["data"]["order_id"] == "order123"


@pytest.mark.asyncio
async def test_upstox_data_instantiation():
    data = UpstoxData(auth_token="test")
    assert isinstance(data, UpstoxData)
