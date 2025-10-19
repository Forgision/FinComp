import copy
import importlib
import traceback
from typing import Any, Dict, Optional, Tuple

from app.db.models.analyzer_db import async_log_analyzer
from app.db.models.apilog_db import async_log_order, executor
from app.db.models.auth_db import get_auth_token_broker
from app.db.models.settings_db import get_analyze_mode
from app.web.backend.schemas.order_schemas import OrderData
from app.core.services.telegram_alert_service import telegram_alert_service

from app.utils.logging import logger
from app.utils.web.socketio import socketio


def import_broker_module(broker_name: str) -> Optional[Any]:
    """
    Dynamically import the broker-specific order API module.

    Args:
        broker_name: Name of the broker

    Returns:
        The imported module or None if import fails
    """
    try:
        module_path = f'app.web.broker.{broker_name}.api.order_api'
        broker_module = importlib.import_module(module_path)
        return broker_module
    except ImportError as error:
        logger.error(f"Error importing broker module '{module_path}': {error}")
        return None

def emit_analyzer_error(request_data: Dict[str, Any], error_message: str) -> Dict[str, Any]:
    """
    Helper function to emit analyzer error events

    Args:
        request_data: Original request data
        error_message: Error message to emit

    Returns:
        Error response dictionary
    """
    error_response = {
        'mode': 'analyze',
        'status': 'error',
        'message': error_message
    }

    # Store complete request data without apikey
    analyzer_request = request_data.copy()
    if 'apikey' in analyzer_request:
        del analyzer_request['apikey']
    analyzer_request['api_type'] = 'placeorder'

    # Log to analyzer database
    executor.submit(async_log_analyzer, analyzer_request, error_response, 'placeorder')

    # Emit socket event
    socketio.emit('analyzer_update', {
        'request': analyzer_request,
        'response': error_response
    })

    return error_response

def place_order_with_auth(
    order_data: Dict[str, Any],
    auth_token: str,
    broker: str,
    original_data: Dict[str, Any]
) -> Tuple[bool, Dict[str, Any], int]:
    """
    Place an order using provided auth token.

    Args:
        order_data: Validated order data
        auth_token: Authentication token for the broker API
        broker: Name of the broker
        original_data: Original request data for logging

    Returns:
        Tuple containing:
        - Success status (bool)
        - Response data (dict)
        - HTTP status code (int)
    """
    order_request_data = copy.deepcopy(original_data)
    if 'apikey' in order_request_data:
        order_request_data.pop('apikey', None)

    # If in analyze mode, route to sandbox for virtual trading
    if get_analyze_mode():
        from app.core.services.sandbox_service import sandbox_place_order

        # Get API key from original data
        api_key = original_data.get('apikey')
        if not api_key:
            error_response = {
                'status': 'error',
                'message': 'API key required for sandbox mode',
                'mode': 'analyze'
            }
            return False, error_response, 400

        # Route to sandbox
        return sandbox_place_order(order_data, api_key, original_data)

    # If not in analyze mode, proceed with actual order placement
    broker_module = import_broker_module(broker)
    if broker_module is None:
        error_response = {
            'status': 'error',
            'message': 'Broker-specific module not found'
        }
        executor.submit(async_log_order, 'placeorder', original_data, error_response)
        return False, error_response, 404

    try:
        # Call the broker's place_order_api function
        res, response_data, order_id = broker_module.place_order_api(order_data, auth_token)
    except Exception as e:
        logger.error(f"Error in broker_module.place_order_api: {e}")
        traceback.print_exc()
        error_response = {
            'status': 'error',
            'message': 'Failed to place order due to internal error'
        }
        executor.submit(async_log_order, 'placeorder', original_data, error_response)
        return False, error_response, 500

    if res.status == 200:
        socketio.emit('order_event', {
            'symbol': order_data['symbol'],
            'action': order_data['action'],
            'orderid': order_id,
            'exchange': order_data.get('exchange', 'Unknown'),
            'price_type': order_data.get('price_type', 'Unknown'),
            'product_type': order_data.get('product_type', 'Unknown'),
            'mode': 'live'
        })
        order_response_data = {'status': 'success', 'orderid': order_id}
        executor.submit(async_log_order, 'placeorder', order_request_data, order_response_data)
        # Send Telegram alert asynchronously
        telegram_alert_service.send_order_alert('placeorder', order_data, order_response_data, order_data.get('apikey'))
        return True, order_response_data, 200
    else:
        message = response_data.get('message', 'Failed to place order') if isinstance(response_data, dict) else 'Failed to place order'
        error_response = {
            'status': 'error',
            'message': message
        }
        executor.submit(async_log_order, 'placeorder', original_data, error_response)
        return False, error_response, res.status if res.status != 200 else 500

def place_order(
    order_data: OrderData,
    api_key: Optional[str] = None,
    auth_token: Optional[str] = None,
    broker: Optional[str] = None
) -> Tuple[bool, Dict[str, Any], int]:
    """
    Place an order with the broker.
    Supports both API-based authentication and direct internal calls.

    Args:
        order_data: Pydantic model containing validated order data
        api_key: OpenAlgo API key (for API-based calls)
        auth_token: Direct broker authentication token (for internal calls)
        broker: Direct broker name (for internal calls)

    Returns:
        Tuple containing:
        - Success status (bool)
        - Response data (dict)
        - HTTP status code (int)
    """
    # Pydantic has already validated the data, so we can proceed.
    # We'll use the model_dump method to get a dictionary.
    order_dict = order_data.model_dump()
    original_data = copy.deepcopy(order_dict)

    if api_key:
        original_data['apikey'] = api_key

    # Case 1: API-based authentication
    if api_key and not (auth_token and broker):
        AUTH_TOKEN, broker_name = get_auth_token_broker(api_key)
        if AUTH_TOKEN is None:
            error_response = {
                'status': 'error',
                'message': 'Invalid openalgo apikey'
            }
            # Skip logging for invalid API keys to prevent database flooding
            return False, error_response, 403

        return place_order_with_auth(order_dict, AUTH_TOKEN, broker_name, original_data)

    # Case 2: Direct internal call with auth_token and broker
    elif auth_token and broker:
        return place_order_with_auth(order_dict, auth_token, broker, original_data)

    # Case 3: Invalid parameters
    else:
        error_response = {
            'status': 'error',
            'message': 'Either api_key or both auth_token and broker must be provided'
        }
        return False, error_response, 400
