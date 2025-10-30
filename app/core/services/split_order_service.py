import asyncio
import copy
import importlib
from typing import Any, Dict, Optional, Tuple

from app.core.schemas.analyzer_db import async_log_analyzer
from app.core.schemas.apilog_db import async_log_order
from app.core.schemas.auth_db import get_auth_token_broker
from app.core.schemas.settings_db import get_analyze_mode
from app.core.services.telegram_alert_service import telegram_alert_service
from sqlalchemy.orm import Session
from app.core.schemas.session import get_db

from app.utils.logging import logger
from app.utils.web.socketio import sio

# Maximum number of orders allowed
MAX_ORDERS = 100


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
    analyzer_request['api_type'] = 'splitorder'
    db = next(get_db())

    # Log to analyzer database
    await async_log_analyzer(db, analyzer_request, error_response, 'splitorder')

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
    try:
        module_path = f'app.web.broker.{broker_name}.api.order_api'
        broker_module = importlib.import_module(module_path)
        return broker_module
    except ImportError as error:
        logger.error(f"Error importing broker module '{module_path}': {error}")
        return None


async def place_single_order(
    order_data: Dict[str, Any],
    broker_module: Any,
    auth_token: str,
    order_num: int,
    total_orders: int
) -> Dict[str, Any]:
    """
    Place a single order and emit event

    Args:
        order_data: Order data
        broker_module: Broker module
        auth_token: Authentication token
        order_num: Order number in the sequence
        total_orders: Total number of orders

    Returns:
        Order result dictionary
    """
    try:
        # Place the order using place_order_api
        res, response_data, order_id = broker_module.place_order_api(
            order_data, auth_token)

        if res.status == 200:
            # Emit order event for toast notification with batch info
            await sio.emit('order_event', {
                'symbol': order_data['symbol'],
                'action': order_data['action'],
                'orderid': order_id,
                'exchange': order_data.get('exchange', 'Unknown'),
                'price_type': order_data.get('pricetype', 'Unknown'),
                'product_type': order_data.get('product', 'Unknown'),
                'mode': 'live',
                'order_num': order_num,
                'quantity': int(order_data['quantity']),
                'batch_order': True,
                'is_last_order': order_num == total_orders
            })

            # Return response without batch info
            return {
                'order_num': order_num,
                'quantity': int(order_data['quantity']),
                'status': 'success',
                'orderid': order_id
            }
        else:
            message = response_data.get('message', 'Failed to place order') if isinstance(
                response_data, dict) else 'Failed to place order'
            return {
                'order_num': order_num,
                'quantity': int(order_data['quantity']),
                'status': 'error',
                'message': message
            }

    except Exception as e:
        logger.error(f"Error placing order {order_num}: {e}")
        return {
            'order_num': order_num,
            'quantity': int(order_data['quantity']),
            'status': 'error',
            'message': 'Failed to place order due to internal error'
        }


async def split_order_with_auth(
    db: Session,
    split_data: Dict[str, Any],
    auth_token: str,
    broker: str,
    original_data: Dict[str, Any]
) -> Tuple[bool, Dict[str, Any], int]:
    """
    Split a large order into multiple orders of specified size using provided auth token.

    Args:
        split_data: Split order data
        auth_token: Authentication token for the broker API
        broker: Name of the broker
        original_data: Original request data for logging

    Returns:
        Tuple containing:
        - Success status (bool)
        - Response data (dict)
        - HTTP status code (int)
    """
    split_request_data = copy.deepcopy(original_data)
    if 'apikey' in split_request_data:
        split_request_data.pop('apikey', None)

    # Validate quantities
    try:
        split_size = int(split_data['splitsize'])
        total_quantity = int(split_data['quantity'])
        if split_size <= 0:
            error_message = 'Split size must be greater than 0'
            if get_analyze_mode(db) is True:
                return False, await emit_analyzer_error(original_data, error_message), 400
            error_response = {'status': 'error', 'message': error_message}
            await async_log_order(db, 'splitorder', original_data, error_response)
            return False, error_response, 400

        # Calculate number of full-size orders and remaining quantity
        num_full_orders = total_quantity // split_size
        remaining_qty = total_quantity % split_size

        # Check if total number of orders exceeds limit
        total_orders = num_full_orders + (1 if remaining_qty > 0 else 0)
        if total_orders > MAX_ORDERS:
            error_message = f'Total number of orders would exceed maximum limit of {MAX_ORDERS}'
            if get_analyze_mode(db) is True:
                return False, await emit_analyzer_error(original_data, error_message), 400
            error_response = {'status': 'error', 'message': error_message}
            await async_log_order(db, 'splitorder', original_data, error_response)
            return False, error_response, 400

    except ValueError:
        error_message = 'Invalid quantity or split size'
        if get_analyze_mode(db) is True:
            return False, await emit_analyzer_error(original_data, error_message), 400
        error_response = {'status': 'error', 'message': error_message}
        await async_log_order(db, 'splitorder', original_data, error_response)
        return False, error_response, 400

    # If in analyze mode, route to sandbox for virtual trading
    if get_analyze_mode(db) is True:
        from app.core.services.sandbox_service import sandbox_place_order

        api_key = original_data.get('apikey')
        if not api_key:
            return False, await emit_analyzer_error(original_data, 'API key required for sandbox mode'), 400

        analyze_results = []
        tasks = []

        # Place full-size orders in sandbox
        for i in range(num_full_orders):
            order_data = copy.deepcopy(split_data)
            order_data['quantity'] = str(split_size)
            order_data['apikey'] = api_key
            tasks.append(sandbox_place_order(
                db, order_data, api_key, {'apikey': api_key, 'order_type': 'split'}))

        # Place remaining quantity order if any
        if remaining_qty > 0:
            order_data = copy.deepcopy(split_data)
            order_data['quantity'] = str(remaining_qty)
            order_data['apikey'] = api_key
            tasks.append(sandbox_place_order(
                db, order_data, api_key, {'apikey': api_key, 'order_type': 'split'}))

        results = await asyncio.gather(*tasks)

        for i, result in enumerate(results):
            success, response, status_code = result
            if success:
                analyze_results.append({
                    'order_num': i + 1,
                    'quantity': split_size if i < num_full_orders else remaining_qty,
                    'status': 'success',
                    'orderid': response.get('orderid')
                })
            else:
                analyze_results.append({
                    'order_num': i + 1,
                    'quantity': split_size if i < num_full_orders else remaining_qty,
                    'status': 'error',
                    'message': response.get('message', 'Order placement failed')
                })

        response_data = {
            'mode': 'analyze',
            'status': 'success',
            'total_quantity': total_quantity,
            'split_size': split_size,
            'results': analyze_results
        }

        # Store complete request data without apikey
        analyzer_request = split_request_data.copy()
        analyzer_request['api_type'] = 'splitorder'

        # Log to analyzer database
        await async_log_analyzer(db, analyzer_request, response_data, 'splitorder')

        # Emit socket event for toast notification
        await sio.emit('analyzer_update', {
            'request': analyzer_request,
            'response': response_data
        })

        # Send Telegram alert for analyze mode
        await telegram_alert_service.send_order_alert(db, 'splitorder', split_data, response_data, split_data.get('apikey'))
        return True, response_data, 200

    # Live mode - process actual orders
    broker_module = import_broker_module(broker)
    if broker_module is None:
        error_response = {
            'status': 'error',
            'message': 'Broker-specific module not found'
        }
        await async_log_order(db, 'splitorder', original_data, error_response)
        return False, error_response, 404

    # Process orders concurrently
    tasks = []
    # Submit full-size orders
    for i in range(num_full_orders):
        order_data = copy.deepcopy(split_data)
        order_data['quantity'] = str(split_size)
        tasks.append(place_single_order(
            order_data, broker_module, auth_token, i + 1, total_orders))

    # Submit remaining quantity order if any
    if remaining_qty > 0:
        order_data = copy.deepcopy(split_data)
        order_data['quantity'] = str(remaining_qty)
        tasks.append(place_single_order(
            order_data, broker_module, auth_token, total_orders, total_orders))

    results = await asyncio.gather(*tasks)
    # Sort results by order_num to maintain order in response
    results.sort(key=lambda x: x['order_num'])

    # Log the split order results
    response_data = {
        'status': 'success',
        'total_quantity': total_quantity,
        'split_size': split_size,
        'results': results
    }
    await async_log_order(db, 'splitorder', split_request_data, response_data)

    # Send Telegram alert for live mode
    await telegram_alert_service.send_order_alert(db, 'splitorder', split_data, response_data, split_data.get('apikey'))

    return True, response_data, 200


async def split_order(
    db: Session,
    split_data: Dict[str, Any],
    api_key: Optional[str] = None,
    auth_token: Optional[str] = None,
    broker: Optional[str] = None
) -> Tuple[bool, Dict[str, Any], int]:
    """
    Split a large order into multiple orders of specified size.
    Supports both API-based authentication and direct internal calls.

    Args:
        split_data: Split order data
        api_key: OpenAlgo API key (for API-based calls)
        auth_token: Direct broker authentication token (for internal calls)
        broker: Direct broker name (for internal calls)

    Returns:
        Tuple containing:
        - Success status (bool)
        - Response data (dict)
        - HTTP status code (int)
    """
    original_data = copy.deepcopy(split_data)
    if api_key:
        original_data['apikey'] = api_key

    # Case 1: API-based authentication
    if api_key and not (auth_token and broker):
        # Add API key to split data
        split_data['apikey'] = api_key

        auth_details = get_auth_token_broker(db, api_key)
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

        return await split_order_with_auth(db, split_data, AUTH_TOKEN, broker_name, original_data)

    # Case 2: Direct internal call with auth_token and broker
    elif auth_token and broker:
        return await split_order_with_auth(db, split_data, auth_token, broker, original_data)

    # Case 3: Invalid parameters
    else:
        error_response = {
            'status': 'error',
            'message': 'Either api_key or both auth_token and broker must be provided'
        }
        return False, error_response, 400
