import pytest
from unittest.mock import AsyncMock, patch, Mock

from app.core.services.orderbook_service import get_orderbook

@pytest.fixture
def mock_broker_module():
    """Fixture to mock broker-specific functions."""
    with patch('app.core.services.orderbook_service.import_broker_module') as mock_import:
        # get_order_book is an async function
        async def get_order_book_side_effect(*args, **kwargs):
            return {"status": "success", "data": [{"symbol": "TEST"}]}

        # These mapping functions are called synchronously in the service
        def map_order_data_side_effect(*args, **kwargs):
            return [{"symbol": "TEST", "mapped": True}]

        def transform_order_data_side_effect(*args, **kwargs):
            return [{"symbol": "TEST", "transformed": True}]

        def calculate_order_statistics_side_effect(*args, **kwargs):
            return {"total": 1}

        mock_broker_funcs = {
            'get_order_book': AsyncMock(side_effect=get_order_book_side_effect),
            'map_order_data': Mock(side_effect=map_order_data_side_effect),
            'calculate_order_statistics': Mock(side_effect=calculate_order_statistics_side_effect),
            'transform_order_data': Mock(side_effect=transform_order_data_side_effect)
        }
        mock_import.return_value = mock_broker_funcs
        yield mock_broker_funcs

@pytest.mark.anyio
async def test_get_orderbook_success_with_auth_token(mock_broker_module):
    """Test get_orderbook with a valid auth_token."""
    auth_token = "some_auth_token"
    broker = "test_broker"
    db = Mock()

    success, response, status_code = await get_orderbook(db, auth_token=auth_token, broker=broker)

    assert success
    assert status_code == 200
    assert "orders" in response["data"]
    assert "statistics" in response["data"]
    # Assert the final transformed data after formatting
    assert response["data"]["orders"] == [{"symbol": "TEST", "transformed": 1.0}]
    assert response["data"]["statistics"] == {"total": 1.0}
    # Verify mocks were called correctly
    mock_broker_module['get_order_book'].assert_awaited_once_with(auth_token)
    mock_broker_module['map_order_data'].assert_called_once()
    mock_broker_module['transform_order_data'].assert_called_once()
    mock_broker_module['calculate_order_statistics'].assert_called_once()

@pytest.mark.anyio
async def test_get_orderbook_success_with_api_key():
    """Test get_orderbook with a valid API key (analyze mode)."""
    api_key = "some_api_key"
    db = Mock()

    with patch('app.core.services.orderbook_service.get_analyze_mode', return_value=True) as mock_get_analyze_mode, \
         patch('app.core.services.orderbook_service.get_auth_token_broker', return_value=("mock_token", "mock_broker")) as mock_get_auth_token, \
         patch('app.core.services.orderbook_service.OrderManager') as MockOrderManager:

            # OrderManager.get_orderbook is a synchronous method
            mock_order_manager_instance = MockOrderManager.return_value
            mock_order_manager_instance.get_orderbook.return_value = (True, {
                'status': 'success',
                'data': {
                    'orders': [{"symbol": "SANDBOX", "quantity": 10}],
                    'statistics': {"total_orders": 1}
                }
            }, 200)

            success, response, status_code = await get_orderbook(db, api_key=api_key)

            # Assertions
            mock_get_analyze_mode.assert_called_once()
            mock_get_auth_token.assert_called_once_with(db, api_key)
            MockOrderManager.assert_called_once_with(user_id=api_key)
            mock_order_manager_instance.get_orderbook.assert_called_once()

    assert success
    assert status_code == 200
    assert "orders" in response["data"]
    assert "statistics" in response["data"]
    assert response["data"]["orders"] == [{"symbol": "SANDBOX", "quantity": 10}]
    assert response["data"]["statistics"] == {"total_orders": 1}

@pytest.mark.anyio
async def test_get_orderbook_no_auth_or_api_key():
    """Test get_orderbook without auth_token or api_key."""
    db = Mock()
    success, response, status_code = await get_orderbook(db)

    assert not success
    assert status_code == 400
    assert "message" in response
    assert response["message"] == "Either api_key or both auth_token and broker must be provided"

@pytest.mark.anyio
async def test_get_orderbook_broker_module_not_found():
    """Test get_orderbook when broker module cannot be imported."""
    db = Mock()
    with patch('app.core.services.orderbook_service.import_broker_module', return_value=None):
        success, response, status_code = await get_orderbook(db, auth_token="token", broker="non_existent_broker")

        assert not success
        assert status_code == 404
        assert "message" in response
        assert response["message"] == "Broker-specific module not found"
