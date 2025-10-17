import pytest
from fastapi.testclient import TestClient
from app.web.main import _app as app # Import the underlying FastAPI app
from app.db.session import get_db
from app.utils.session import check_session_validity_fastapi
from app.db.user_db import add_user, delete_user_by_username
from app.db.auth_db import upsert_api_key, delete_api_key_by_username


@pytest.fixture(name="client")
def client_fixture():
    with TestClient(app, follow_redirects=True) as client_instance:
        yield client_instance

@pytest.fixture(name="test_user")
def test_user_fixture():
    username = "testuser"
    email = "test@example.com"
    password = "testpassword"
    api_key = "testapikey"

    # Create a test user and API key
    db = next(get_db())
    try:
        add_user(db, username, email, password, True)
        upsert_api_key(username, api_key)
        db.commit() # Commit changes after creating user and API key

        yield {
            "username": username,
            "email": email,
            "password": password,
            "api_key": api_key
        }
    finally:
        # Clean up the test user and API key using the same session
        delete_api_key_by_username(db, username)
        delete_user_by_username(db, username)
        db.close()

def test_dashboard_access_unauthenticated(client):
    response = client.get("/dashboard/dashboard")
    assert response.status_code == 303
    assert '{"message":"Not authenticated"}' in response.text

def test_dashboard_access_authenticated(client, test_user):
    response = client.post(
        "/auth/login",
        data={"username": test_user["username"], "password": test_user["password"]},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert '{"status":"success"}' in response.text


@pytest.fixture
def test_client_with_mocks(test_user, mocker):
    # Mock check_session_validity_fastapi directly within the fixture
    async def mock_check_session_validity_fastapi():
        return {"user": test_user["username"], "broker": "test_broker"}
    app.dependency_overrides[check_session_validity_fastapi] = mock_check_session_validity_fastapi

    # Apply mocks before creating the TestClient
    mocker.patch('app.db.settings_db.get_analyze_mode', return_value=True)
    mocker.patch('app.web.backend.routes.orders.get_analyze_mode', return_value=True)
    
    # Mock request.session.get to provide user and broker directly
    mocker.patch('starlette.requests.Request.session', new_callable=mocker.PropertyMock, return_value={
        "user": test_user["username"],
        "broker": "test_broker"
    })
    
    # Mock the get_orderbook service call
    mock_orderbook_data = {
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
    mocker.patch('app.web.backend.routes.orders.get_orderbook', new_callable=mocker.AsyncMock, return_value=(True, mock_orderbook_data, 200))
    mocker.patch('app.web.backend.routes.orders.get_auth_token', return_value="mock_auth_token")
    mocker.patch('app.web.backend.routes.orders.get_api_key_for_tradingview', return_value=test_user["api_key"])

    # Mock the broker module import for the test_broker (though not strictly needed if get_analyze_mode is True)
    mock_broker_funcs = {
        'get_order_book': mocker.AsyncMock(return_value={"status": "success", "data": []}),
        'map_order_data': mocker.Mock(return_value=[]),
        'calculate_order_statistics': mocker.Mock(return_value={}),
        'transform_order_data': mocker.Mock(return_value=[])
    }
    mocker.patch('app.web.services.orderbook_service.import_broker_module', return_value=mock_broker_funcs)

    # Create and yield the TestClient after mocks are applied
    with TestClient(app, follow_redirects=True) as client_with_mocks:
        yield client_with_mocks
    app.dependency_overrides = {} # Clear overrides


def test_orderbook_access_authenticated(test_client_with_mocks):
    response = test_client_with_mocks.get("/api/v1/orders/orderbook")
    assert response.status_code == 200
    assert "Order Book" in response.text
    assert "AAPL" in response.text
    assert "10" in response.text
    assert "150" in response.text
    assert "Buy Orders" in response.text
    assert "1" in response.text # Asserting for the value of total_buy_orders
