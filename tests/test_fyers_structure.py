import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.brokers.fyers import FyersAuth, FyersAccount, FyersData
from app.core.brokers.base import AuthConfig


@pytest.mark.asyncio
async def test_fyers_auth_instantiation():
    auth = FyersAuth()
    assert isinstance(auth, FyersAuth)


@pytest.mark.asyncio
async def test_fyers_auth_authenticate():
    auth = FyersAuth()
    config = AuthConfig(
        auth_code="test_code", api_key="test_key", api_secret="test_secret"
    )

    with patch("app.core.brokers.fyers.fyers_auth.get_httpx_client") as mock_get_client:
        mock_client = MagicMock()
        mock_post = AsyncMock()
        mock_client.post = mock_post
        mock_get_client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "s": "ok",
            "access_token": "token123",
            "refresh_token": "refresh123",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        response = await auth.authenticate(config)
        assert response.access_token == "token123"
        assert response.refresh_token == "refresh123"
        assert response.status == "success"
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_fyers_auth_missing_credentials():
    auth = FyersAuth()
    # Missing api_key/secret
    config = AuthConfig(auth_code="test_code")

    with pytest.raises(ValueError, match="api_key and api_secret are required"):
        await auth.authenticate(config)


@pytest.mark.asyncio
async def test_fyers_account_instantiation():
    account = FyersAccount()
    assert isinstance(account, FyersAccount)


@pytest.mark.asyncio
async def test_fyers_account_place_order():
    account = FyersAccount()
    order_data = {
        "symbol": "NSE:SBIN-EQ",
        "quantity": 1,
        "pricetype": "MARKET",
        "action": "BUY",
        "product": "MIS",
        "exchange": "NSE",
    }

    # We need to mock get_br_symbol since transform_data calls it (and it's async now)
    # Patches need to be applied where the symbol is imported/used.
    # transform_data imports get_br_symbol from app.core.schemas.token_db

    with (
        patch(
            "app.core.brokers.fyers.fyers_account.get_httpx_client"
        ) as mock_get_client,
        patch(
            "app.core.brokers.fyers.mapping.transform_data.get_br_symbol",
            new_callable=AsyncMock,
        ) as mock_get_br_symbol,
    ):
        mock_client = MagicMock()
        mock_post = AsyncMock()
        mock_client.post = mock_post
        mock_get_client.return_value = mock_client

        mock_get_br_symbol.return_value = "NSE:SBIN-EQ"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"s": "ok", "id": "order123"}
        mock_post.return_value = mock_response

        response = await account.place_order(order_data, "auth_token")

        # Debug info if fails
        if response.get("s") != "ok":
            print(f"FAILED RESPONSE: {response}")

        assert response["s"] == "ok"
        assert response["id"] == "order123"


@pytest.mark.asyncio
async def test_fyers_data_instantiation():
    data = FyersData(auth_token="test")
    assert isinstance(data, FyersData)


@pytest.mark.asyncio
async def test_fyers_data_get_quotes():
    data = FyersData(auth_token="test")

    with (
        patch("app.core.brokers.fyers.fyers_data.get_httpx_client") as mock_get_client,
        patch(
            "app.core.brokers.fyers.fyers_data.get_br_symbol", new_callable=AsyncMock
        ) as mock_get_sym,
    ):
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        mock_get_sym.return_value = "NSE:SBIN-EQ"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "s": "ok",
            "d": [{"v": {"lp": 100.0, "volume": 1000}}],
        }
        mock_client.get.return_value = mock_response

        quotes = await data.get_quotes("SBIN", "NSE")
        assert quotes["ltp"] == 100.0
