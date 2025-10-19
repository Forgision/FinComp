import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import Request
from fastapi.testclient import TestClient

from app.db.models.auth_db import delete_api_key_by_username, upsert_api_key
from app.db.models.session import get_db
from app.db.models.user_db import add_user, delete_user_by_username
from app.main import _app as app_fastapi  # Import the underlying FastAPI app
from app.utils.session import check_session_validity_fastapi


class TestAPIEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app_fastapi, follow_redirects=False)
        self.db = next(get_db())

        self.username = "testuser"
        self.email = "test@example.com"
        self.password = "testpassword"
        self.api_key = "testapikey"

        # Create a test user and API key
        add_user(self.username, self.email, self.password, True)
        upsert_api_key(self.username, self.api_key)
        self.db.commit()

        # Mock check_session_validity_fastapi
        async def mock_check_session_validity_fastapi(request: Request):
            return self.username

        self.check_session_patch = patch('app.utils.session.check_session_validity_fastapi', new=mock_check_session_validity_fastapi)
        self.check_session_patch.start()
        app_fastapi.dependency_overrides[check_session_validity_fastapi] = mock_check_session_validity_fastapi

        # Mock get_db dependency
        def override_get_db():
            try:
                yield self.db
            finally:
                self.db.close()
        app_fastapi.dependency_overrides[get_db] = override_get_db

        # Mock get_analyze_mode
        self.get_analyze_mode_patch_db = patch('app.db.models.settings_db.get_analyze_mode', return_value=True)
        self.get_analyze_mode_patch_db.start()
        self.get_analyze_mode_patch_routes = patch('app.web.backend.routes.orders.get_analyze_mode', return_value=True)
        self.get_analyze_mode_patch_routes.start()

        # Mock request.session.get
        self.session_patch = patch('starlette.requests.Request.session', new_callable=MagicMock, return_value={
            "user": self.username,
            "broker": "test_broker"
        })
        self.session_patch.start()

        # Mock the get_orderbook service call
        self.mock_orderbook_data = {
            "data": {
                "orders": [
                    {"symbol": "AAPL", "exchange": "NSE", "action": "BUY", "quantity": 10, "price": 150, "orderid": "123"},
                ],
                "statistics": {
                    "total_buy_orders": 1,
                    "total_sell_orders": 0,
                    "total_completed_orders": 1,
                    "total_open_orders": 0,
                    "total_rejected_orders": 0
                }
            }
        }
        self.get_orderbook_patch = patch('app.web.backend.routes.orders.get_orderbook', new_callable=AsyncMock, return_value=(True, self.mock_orderbook_data, 200))
        self.get_orderbook_patch.start()

        self.get_auth_token_patch = patch('app.web.backend.routes.orders.get_auth_token', return_value="mock_auth_token")
        self.get_auth_token_patch.start()

        self.get_api_key_for_tradingview_patch = patch('app.web.backend.routes.orders.get_api_key_for_tradingview', return_value=self.api_key)
        self.get_api_key_for_tradingview_patch.start()

        # Mock the broker module import for the test_broker (though not strictly needed if get_analyze_mode is True)
        self.mock_broker_funcs = {
            'get_order_book': AsyncMock(return_value={"status": "success", "data": self.mock_orderbook_data['data']}),
            'map_order_data': MagicMock(return_value=[]),
            'calculate_order_statistics': MagicMock(return_value={}),
            'transform_order_data': MagicMock(return_value=[])
        }
        self.import_broker_module_patch = patch('app.core.services.orderbook_service.import_broker_module', return_value=self.mock_broker_funcs)
        self.import_broker_module_patch.start()


    def tearDown(self):
        # Clean up the test user and API key
        delete_api_key_by_username(self.db, self.username)
        delete_user_by_username(self.username)
        self.db.close()

        # Stop all patches
        self.check_session_patch.stop()
        self.get_analyze_mode_patch_db.stop()
        self.get_analyze_mode_patch_routes.stop()
        self.session_patch.stop()
        self.get_orderbook_patch.stop()
        self.get_auth_token_patch.stop()
        self.get_api_key_for_tradingview_patch.stop()
        self.import_broker_module_patch.stop()

        app_fastapi.dependency_overrides = {}  # Clear overrides

    def test_dashboard_access_unauthenticated(self):
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['location'], '/auth/login')

    def test_dashboard_access_authenticated(self):
        response = self.client.post(
            "/auth/login",
            data={"username": self.username, "password": self.password},
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('{"status":"success"}', response.text)

    @unittest.skip('testing in future')
    def test_orderbook_access_authenticated(self):
        response = self.client.get("/api/v1/orders/orderbook")
        if response.status_code != 200:
            print(f"Orderbook API response status: {response.status_code}")
            print(f"Orderbook API response content: {response.text}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Order Book", response.text)
        self.assertIn("AAPL", response.text)
        self.assertIn("10", response.text)
        self.assertIn("150", response.text)
        self.assertIn("Buy Orders", response.text)
        self.assertIn("1", response.text) # Asserting for the value of total_buy_orders

if __name__ == '__main__':
    unittest.main()
