import pytest
import asyncio
from app.core.services.holdings_service import get_holdings
from unittest.mock import MagicMock, patch, AsyncMock

@pytest.mark.asyncio
async def test_get_holdings_is_async_and_works():
    """
    This test confirms that get_holdings is now async and can be awaited.
    """
    db = AsyncMock()
    # Mock db.execute to return a Result object with scalars().first()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = MagicMock(analyze_mode=False)
    db.execute.return_value = mock_result

    # Check if it is a coroutine function
    is_coroutine = asyncio.iscoroutinefunction(get_holdings)
    assert is_coroutine, "get_holdings should be async"

    # We need to mock get_analyze_mode because it's called inside
    with patch("app.core.schemas.settings_db.get_analyze_mode", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = False

        # Mock import_broker_module
        with patch("app.core.services.holdings_service.import_broker_module") as mock_import:
            # Setup mock return value
            mock_broker_funcs = {
                "get_holdings": AsyncMock(return_value={"status": "success", "holdings": []}),
                "map_portfolio_data": MagicMock(return_value=[]),
                "calculate_portfolio_statistics": MagicMock(return_value={}),
                "transform_holdings_data": MagicMock(return_value=[])
            }
            mock_import.return_value = mock_broker_funcs

            # Test call with auth_token and broker (internal call path)
            success, response, status_code = await get_holdings(
                db, auth_token="test_token", broker="test_broker"
            )

            assert success is True
            assert status_code == 200
            assert "data" in response

            # Verify broker function was called
            mock_broker_funcs["get_holdings"].assert_awaited_once_with("test_token")

@pytest.mark.asyncio
async def test_get_holdings_analyze_mode():
    """
    Test analyze mode path
    """
    db = AsyncMock()

    # Mock get_analyze_mode
    # Patch get_auth_token_broker WHERE IT IS USED
    with patch("app.core.schemas.settings_db.get_analyze_mode", new_callable=AsyncMock) as mock_analyze, \
         patch("app.core.services.holdings_service.get_auth_token_broker", new_callable=AsyncMock) as mock_get_token, \
         patch("app.core.services.sandbox_service.sandbox_get_holdings", new_callable=AsyncMock) as mock_sandbox:

        mock_analyze.return_value = True
        mock_get_token.return_value = ("fake_token", "fake_broker")
        mock_sandbox.return_value = (True, {"status": "success"}, 200)

        success, response, status_code = await get_holdings(
            db, api_key="test_api_key"
        )

        assert success is True
        mock_sandbox.assert_awaited()
