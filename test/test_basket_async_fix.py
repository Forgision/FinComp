import pytest
import asyncio
import inspect
from unittest.mock import MagicMock, AsyncMock, patch
from app.core.services.basket_order_service import process_basket_order_with_auth

# Mock broker module
mock_broker = MagicMock()
mock_broker.place_order_api = AsyncMock(return_value=(MagicMock(status=200), {}, "123"))

@pytest.mark.asyncio
async def test_basket_order_async_broker():
    """
    Test that basket order service correctly awaits async broker functions.
    """
    # Mock database session
    mock_db = AsyncMock()

    # Mock basket data
    basket_data = {
        "strategy": "strat_1",
        "orders": [
            {"symbol": "INFY", "action": "BUY", "quantity": 10},
            {"symbol": "TCS", "action": "SELL", "quantity": 5}
        ]
    }

    # Mock imports
    with patch("app.core.services.basket_order_service.import_broker_module", return_value=mock_broker), \
         patch("app.core.services.basket_order_service.async_log_order", new_callable=AsyncMock), \
          patch("app.core.services.basket_order_service.telegram_alert_service", new_callable=AsyncMock), \
         patch("app.core.services.basket_order_service.get_analyze_mode", new_callable=AsyncMock, return_value=False):

        # Run the function
        try:
            success, response, status = await process_basket_order_with_auth(
                mock_db, basket_data, "token", "mock_broker", basket_data
            )
            # If we reach here, we must verify that place_order_api was awaited and didn't crash
            assert success is True
            assert len(response["results"]) == 2
            # Check that individual orders succeeded
            for res in response["results"]:
                assert res["status"] == "success", f"Order failed: {res.get('message')}"
        except TypeError as e:
            # This is what we expect to happen before the fix
            # "cannot unpack non-iterable coroutine object"
            print(f"Caught expected TypeError (bug): {e}")
            raise e  # Fail the test to confirm bug exists

if __name__ == "__main__":
    asyncio.run(test_basket_order_async_broker())
