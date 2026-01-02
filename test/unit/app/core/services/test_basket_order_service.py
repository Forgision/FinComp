
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from app.core.services.basket_order_service import place_single_order, process_basket_order_with_auth

# Mock broker module
class AsyncBrokerModule:
    @staticmethod
    async def place_order_api(data, auth):
        await asyncio.sleep(0.01) # Simulate async work
        return MagicMock(status=200), {"status": "success", "id": "123"}, "123"

class SyncBrokerModule:
    @staticmethod
    def place_order_api(data, auth):
        import time
        time.sleep(0.01) # Simulate sync work
        return MagicMock(status=200), {"status": "success", "id": "456"}, "456"

@pytest.mark.asyncio
async def test_place_single_order_async_broker():
    order_data = {"symbol": "TEST", "action": "BUY"}
    result = await place_single_order(
        order_data,
        AsyncBrokerModule,
        "token",
        1,
        0
    )
    assert result["status"] == "success"
    assert result["orderid"] == "123"

@pytest.mark.asyncio
async def test_place_single_order_sync_broker():
    order_data = {"symbol": "TEST", "action": "BUY"}
    result = await place_single_order(
        order_data,
        SyncBrokerModule,
        "token",
        1,
        0
    )
    # The current implementation will FAIL/BLOCK here if not fixed.
    # But wait, place_single_order calls broker_module.place_order_api directly.
    # If SyncBrokerModule is used, it works but blocks.
    # If AsyncBrokerModule is used, it fails because it doesn't await.
    assert result["status"] == "success"
    assert result["orderid"] == "456"

@pytest.mark.asyncio
async def test_process_basket_order_ordering():
    # Mock place_single_order to track execution time/order
    execution_log = []

    async def mock_place_single_order(order_data, *args):
        action = order_data["action"]
        execution_log.append(f"START_{action}")
        await asyncio.sleep(0.01)
        execution_log.append(f"END_{action}")
        return {"action": action}

    with patch("app.core.services.basket_order_service.place_single_order", side_effect=mock_place_single_order) as mock_place:
        with patch("app.core.services.basket_order_service.import_broker_module", return_value=AsyncBrokerModule):
            with patch("app.core.services.basket_order_service.get_analyze_mode", return_value=False):
                with patch("app.core.services.basket_order_service.async_log_order"):
                    with patch("app.core.services.basket_order_service.telegram_alert_service") as mock_alert_service:
                        mock_alert_service.send_order_alert = AsyncMock()

                        basket_data = {
                            "orders": [
                                {"action": "SELL", "symbol": "B"},
                                {"action": "BUY", "symbol": "A"},
                                {"action": "SELL", "symbol": "C"},
                            ],
                            "strategy": "test",
                            "apikey": "key"
                        }

                        await process_basket_order_with_auth(
                            MagicMock(),
                            basket_data,
                            "token",
                            "broker",
                            {}
                        )

                        # Verify BUYs started before SELLs
                        # Note: In the current BROKEN implementation, they are gathered together.
                        # So they start roughly at the same time.
                        # In the FIXED implementation, all BUYs should finish before any SELL starts.

                        buy_indices = [i for i, x in enumerate(execution_log) if "BUY" in x]
                        sell_indices = [i for i, x in enumerate(execution_log) if "SELL" in x]

                        print(execution_log)

                        # Check that last BUY END is before first SELL START
                        last_buy_end = max([i for i, x in enumerate(execution_log) if x == "END_BUY"])
                        first_sell_start = min([i for i, x in enumerate(execution_log) if x == "START_SELL"])

                        assert last_buy_end < first_sell_start, "SELLs started before BUYs finished"
