import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, Optional, Tuple

# We import the functions to test.
from app.core.services.holdings_service import get_holdings

@pytest.mark.asyncio
async def test_get_holdings_async_flow_broker():
    """
    Test that get_holdings is async and awaits broker calls.
    """
    mock_db = AsyncMock()
    mock_api_key = "test_api_key"
    mock_auth_token = "test_auth_token"
    mock_broker = "test_broker"

    # Mock get_analyze_mode to return False
    with patch("app.core.schemas.settings_db.get_analyze_mode", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = False

        # Mock get_auth_token_broker
        with patch("app.core.services.holdings_service.get_auth_token_broker", new_callable=AsyncMock) as mock_get_token:
            mock_get_token.return_value = (mock_auth_token, mock_broker)

            # Mock broker module import
            with patch("app.core.services.holdings_service.import_broker_module") as mock_import:
                # Create a mock broker module with ASYNC functions
                mock_broker_funcs = {
                    "get_holdings": AsyncMock(return_value={"status": "success", "data": []}),
                    "map_portfolio_data": MagicMock(return_value=[]),
                    "calculate_portfolio_statistics": MagicMock(return_value={}),
                    "transform_holdings_data": MagicMock(return_value=[])
                }
                mock_import.return_value = mock_broker_funcs

                # Call get_holdings
                # We expect get_holdings to be async, so we await it.
                success, response, status_code = await get_holdings(mock_db, api_key=mock_api_key)

                assert success is True
                assert status_code == 200

                # Verify get_auth_token_broker was awaited
                mock_get_token.assert_awaited_once_with(mock_db, mock_api_key)

                # Verify broker get_holdings was awaited
                mock_broker_funcs["get_holdings"].assert_awaited_once_with(mock_auth_token)

@pytest.mark.asyncio
async def test_get_holdings_async_flow_sandbox():
    """Test sandbox mode flow."""
    mock_db = AsyncMock()
    mock_api_key = "test_api_key"

    with patch("app.core.schemas.settings_db.get_analyze_mode", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = True

        with patch("app.core.services.holdings_service.get_auth_token_broker", new_callable=AsyncMock) as mock_get_token:
             mock_get_token.return_value = ("token", "broker")

             # Mock sandbox_get_holdings
             with patch("app.core.services.sandbox_service.sandbox_get_holdings", new_callable=AsyncMock) as mock_sandbox:
                mock_sandbox.return_value = (True, {"data": "sandbox"}, 200)

                success, response, status_code = await get_holdings(mock_db, api_key=mock_api_key)

                assert success is True
                mock_analyze.assert_awaited_once_with(mock_db)

                # Verify sandbox call args
                args, _ = mock_sandbox.call_args
                # Expecting: sandbox_get_holdings(db, api_key, original_data)
                assert args[0] == mock_db
                assert args[1] == mock_api_key
