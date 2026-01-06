
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.core.services.holdings_service import get_holdings, get_holdings_with_auth

@pytest.mark.asyncio
async def test_get_holdings_async_structure():
    """
    This test verifies that get_holdings is now a coroutine and can be awaited.
    It mocks the internal dependencies to avoid actual DB/Broker calls.
    """
    # Mock dependencies
    mock_db = MagicMock()

    # Mock get_auth_token_broker
    # Note: get_auth_token_broker is async in the real code, so we mock it as returning a coroutine
    with patch("app.core.services.holdings_service.get_auth_token_broker", new_callable=AsyncMock) as mock_get_token:
        mock_get_token.return_value = ("fake_token", "fake_broker")

        # Mock get_holdings_with_auth
        with patch("app.core.services.holdings_service.get_holdings_with_auth", new_callable=AsyncMock) as mock_internal:
            mock_internal.return_value = (True, {"data": "ok"}, 200)

            # Call get_holdings
            result = await get_holdings(mock_db, api_key="test_key")

            assert result == (True, {"data": "ok"}, 200)
            mock_get_token.assert_awaited_once()
            mock_internal.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_holdings_with_auth_async_broker():
    """
    Test get_holdings_with_auth correctly awaits an async broker function.
    """
    mock_db = MagicMock()

    with patch("app.core.schemas.settings_db.get_analyze_mode", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = False

        # Mock broker module import
        with patch("app.core.services.holdings_service.import_broker_module") as mock_import:
            # Create async mocks for broker functions
            async_get_holdings = AsyncMock(return_value={"status": "success", "data": []})

            # Sync mocks for mapping/transform
            mock_map = MagicMock(return_value=[])
            mock_calc = MagicMock(return_value={})
            mock_transform = MagicMock(return_value=[])

            mock_import.return_value = {
                "get_holdings": async_get_holdings,
                "map_portfolio_data": mock_map,
                "calculate_portfolio_statistics": mock_calc,
                "transform_holdings_data": mock_transform
            }

            result = await get_holdings_with_auth(mock_db, "token", "broker")

            assert result[0] is True
            async_get_holdings.assert_awaited_once_with("token")

@pytest.mark.asyncio
async def test_get_holdings_with_auth_sync_broker():
    """
    Test get_holdings_with_auth correctly handles a synchronous broker function.
    """
    mock_db = MagicMock()

    with patch("app.core.schemas.settings_db.get_analyze_mode", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = False

        # Mock broker module import
        with patch("app.core.services.holdings_service.import_broker_module") as mock_import:
            # Create SYNC mock for broker functions
            sync_get_holdings = MagicMock(return_value={"status": "success", "data": []})

            # Sync mocks for mapping/transform
            mock_map = MagicMock(return_value=[])
            mock_calc = MagicMock(return_value={})
            mock_transform = MagicMock(return_value=[])

            mock_import.return_value = {
                "get_holdings": sync_get_holdings,
                "map_portfolio_data": mock_map,
                "calculate_portfolio_statistics": mock_calc,
                "transform_holdings_data": mock_transform
            }

            result = await get_holdings_with_auth(mock_db, "token", "broker")

            assert result[0] is True
            sync_get_holdings.assert_called_once_with("token")

@pytest.mark.asyncio
async def test_import_broker_module_caching():
    from app.core.services.holdings_service import import_broker_module

    with patch("importlib.import_module") as mock_import:
        mock_api = MagicMock()
        mock_map = MagicMock()

        # Setup mocks to allow getattr
        mock_api.get_holdings = "holdings_func"
        mock_map.map_portfolio_data = "map_func"
        mock_map.calculate_portfolio_statistics = "calc_func"
        mock_map.transform_holdings_data = "trans_func"

        mock_import.side_effect = [mock_api, mock_map]

        # First call
        res1 = import_broker_module("brokerX")

        # Second call
        res2 = import_broker_module("brokerX")

        # Should be same object (dictionary equality)
        assert res1 == res2

        # import_module should have been called only twice (once for api, once for mapping)
        # NOT 4 times.
        assert mock_import.call_count == 2
