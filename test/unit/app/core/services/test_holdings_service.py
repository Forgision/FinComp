import pytest
from unittest.mock import MagicMock, patch
import app.core.services.holdings_service as holdings_service

# Mock async function
async def async_get_holdings(auth_token):
    return {"status": "success", "data": []}

# Mock sync function
def sync_get_holdings(auth_token):
    return {"status": "success", "data": []}

@pytest.mark.asyncio
async def test_get_holdings_async_broker_success():
    """
    Verify that async broker works with async get_holdings service.
    """
    with patch("app.core.schemas.settings_db.get_analyze_mode", new_callable=MagicMock) as mock_get_analyze_mode, \
         patch("app.core.services.holdings_service.import_broker_module") as mock_import:

        # Mock get_analyze_mode to be async and return False
        async def async_false(*args, **kwargs):
            return False
        mock_get_analyze_mode.side_effect = async_false

        # Mock import_broker_module to return our mocks
        mock_import.return_value = {
            "get_holdings": async_get_holdings,
            "map_portfolio_data": lambda x: x,
            "calculate_portfolio_statistics": lambda x: {},
            "transform_holdings_data": lambda x: x,
        }

        # Call the async function
        result = await holdings_service.get_holdings_with_auth(None, "token", "mock_broker", None)

        success, data, status = result
        assert success is True
        assert status == 200

@pytest.mark.asyncio
async def test_get_holdings_sync_broker_success():
    """
    Verify that sync broker works with async get_holdings service (via executor).
    """
    with patch("app.core.schemas.settings_db.get_analyze_mode", new_callable=MagicMock) as mock_get_analyze_mode, \
         patch("app.core.services.holdings_service.import_broker_module") as mock_import:

        async def async_false(*args, **kwargs):
            return False
        mock_get_analyze_mode.side_effect = async_false

        mock_import.return_value = {
            "get_holdings": sync_get_holdings, # SYNC function
            "map_portfolio_data": lambda x: x,
            "calculate_portfolio_statistics": lambda x: {},
            "transform_holdings_data": lambda x: x,
        }

        # Call the async function
        result = await holdings_service.get_holdings_with_auth(None, "token", "mock_broker", None)

        success, data, status = result
        assert success is True
        assert status == 200

@pytest.mark.asyncio
async def test_get_holdings_missing_mapping_module():
    """
    Verify that if mapping module is missing (e.g. Fyers fallback), it defaults gracefully.
    """

    # We will test the import_broker_module function directly
    with patch("importlib.import_module") as mock_import_module:
        # Mock broker module
        mock_broker_module = MagicMock()

        # Setup class instantiation
        class MockAccount:
             def get_holdings(self): pass

        mock_broker_module.FyersAccount = MockAccount

        def side_effect(name):
            if name == "app.core.brokers.fyers":
                return mock_broker_module
            if "mapping" in name:
                raise ImportError("Mapping module missing")
            raise ImportError(f"Unknown: {name}")

        mock_import_module.side_effect = side_effect

        # Test fyers (which triggers the new path)
        funcs = holdings_service.import_broker_module("fyers")

        assert funcs is not None
        assert "get_holdings" in funcs
        # Ensure fallbacks are present
        assert funcs["map_portfolio_data"]("test") == "test"
        assert funcs["calculate_portfolio_statistics"]("test") == {}
