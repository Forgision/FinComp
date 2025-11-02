import copy
import importlib
import traceback
from typing import Any, Dict, Optional, Tuple

from app.core.schemas.analyzer_db import async_log_analyzer
from app.core.schemas.apilog_db import async_log_order
from app.core.schemas.auth_db import get_auth_token_broker
from app.core.schemas.settings_db import get_analyze_mode
from app.core.services.telegram_alert_service import telegram_alert_service
from sqlalchemy.orm import Session
from app.core.schemas import get_db

from app.utils.logging import logger
from app.utils.web.socketio import sio

# Initialize logger


async def emit_analyzer_error(request_data: Dict[str, Any], error_message: str) -> Dict[str, Any]:
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
    analyzer_request['api_type'] = 'cancelorder'
    db = next(get_db())

    # Log to analyzer database
    await async_log_analyzer(analyzer_request, error_response, 'cancelorder')

    # Emit socket event
    await sio.emit('analyzer_update', {
        'request': analyzer_request,
        'response': error_response
    })

    return error_response


def import_broker_module(broker_name: str) -> Optional[Any]:
    """
    Dynamically import the broker-specific order API module.

    Args:
        broker_name: Name of the broker

    Returns:
        The imported module or None if import fails
    """
    module_path = None
    try:
        module_path = f'broker.{broker_name}.api.order_api'
        broker_module = importlib.import_module(module_path)
        return broker_module
    except ImportError as error:
        logger.error(f"Error importing broker module '{module_path}': {error}")
        return None


async def cancel_order_with_auth(
    db: Session,
    orderid: str,
    auth_token: str,
    broker: str,
    original_data: Dict[str, Any]
) -> Tuple[bool, Dict[str, Any], int]:
    """
    Cancel an order using provided auth token.

    Args:
        orderid: Order ID to cancel
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
    if get_analyze_mode() is True:
        from app.core.services.sandbox_service import sandbox_cancel_order

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
        order_data = {'orderid': orderid}
        return await sandbox_cancel_order(db, order_data, api_key, original_data)

    broker_module = import_broker_module(broker)
    if broker_module is None:
        error_response = {
            'status': 'error',
            'message': 'Broker-specific module not found'
        }
        await async_log_order('cancelorder', original_data, error_response)
        return False, error_response, 404

    try:
        # Use the dynamically imported module's function to cancel the order
        response_message, status_code = broker_module.cancel_order(
            orderid, auth_token)
    except Exception as e:
        logger.error(f"Error in broker_module.cancel_order: {e}")
        traceback.print_exc()
        error_response = {
            'status': 'error',
            'message': 'Failed to cancel order due to internal error'
        }
        await async_log_order('cancelorder', original_data, error_response)
        return False, error_response, 500

    if status_code == 200:
        await sio.emit('cancel_order_event', {
            'status': response_message.get('status'),
            'orderid': orderid,
            'mode': 'live'
        })
        order_response_data = {
            'status': 'success',
            'orderid': orderid
        }
        await async_log_order('cancelorder', order_request_data, order_response_data)
        # Send Telegram alert for live mode
        await telegram_alert_service.send_order_alert(db, 'cancelorder', {'orderid': orderid}, order_response_data, original_data.get('apikey'))
        return True, order_response_data, 200
    else:
        message = response_message.get('message', 'Failed to cancel order') if isinstance(
            response_message, dict) else 'Failed to cancel order'
        error_response = {
            'status': 'error',
            'message': message
        }
        await async_log_order('cancelorder', original_data, error_response)
        return False, error_response, status_code


async def cancel_order(
    db: Session,
    orderid: str,
    api_key: Optional[str] = None,
    auth_token: Optional[str] = None,
    broker: Optional[str] = None
) -> Tuple[bool, Dict[str, Any], int]:
    """
    Cancel an order.
    Supports both API-based authentication and direct internal calls.

    Args:
        orderid: Order ID to cancel
        api_key: OpenAlgo API key (for API-based calls)
        auth_token: Direct broker authentication token (for internal calls)
        broker: Direct broker name (for internal calls)

    Returns:
        Tuple containing:
        - Success status (bool)
        - Response data (dict)
        - HTTP status code (int)
    """
    original_data = {'orderid': orderid}
    if api_key:
        original_data['apikey'] = api_key

    # Validate order ID
    if not orderid:
        error_message = 'Order ID is missing'
        error_response = {'status': 'error', 'message': error_message}
        await async_log_order('cancelorder', original_data, error_response)
        return False, error_response, 400

    # Case 1: API-based authentication
    if api_key and not (auth_token and broker):
        auth_details = get_auth_token_broker(db, provided_api_key=api_key)
        if not auth_details or len(auth_details) < 2:
            error_response = {
                'status': 'error',
                'message': 'Invalid openalgo apikey'
            }
            return False, error_response, 403
        AUTH_TOKEN, broker_name = auth_details[0], auth_details[1]
        if AUTH_TOKEN is None or broker_name is None:
            error_response = {
                'status': 'error',
                'message': 'Invalid openalgo apikey'
            }
            # Skip logging for invalid API keys to prevent database flooding
            return False, error_response, 403

        return await cancel_order_with_auth(db, orderid, AUTH_TOKEN, broker_name, original_data)

    # Case 2: Direct internal call with auth_token and broker
    elif auth_token and broker:
        return await cancel_order_with_auth(db, orderid, auth_token, broker, original_data)

    # Case 3: Invalid parameters
    else:
        error_response = {
            'status': 'error',
            'message': 'Either api_key or both auth_token and broker must be provided'
        }
        return False, error_response, 400
