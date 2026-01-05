import importlib
import inspect
import traceback
from typing import Any, Dict, Optional, Tuple

from app.core.schemas.auth_db import get_auth_token_broker
from app.utils.logging import logger


def format_decimal(value):
    """Format numeric value to 2 decimal places"""
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    return value


def format_position_data(position_data):
    """Format all numeric values in position data to 2 decimal places"""
    if isinstance(position_data, list):
        return [
            {
                key: format_decimal(value) if isinstance(value, (int, float)) else value
                for key, value in item.items()
            }
            for item in position_data
        ]
    return position_data


def import_broker_module(broker_name: str) -> Optional[Dict[str, Any]]:
    """
    Dynamically import the broker-specific positionbook modules.

    Args:
        broker_name: Name of the broker

    Returns:
        Dictionary of broker functions or None if import fails
    """
    try:
        # Import API module
        api_module = importlib.import_module(f"broker.{broker_name}.api.order_api")
        # Import mapping module
        mapping_module = importlib.import_module(
            f"broker.{broker_name}.mapping.order_data"
        )
        return {
            "get_positions": getattr(api_module, "get_positions"),
            "map_position_data": getattr(mapping_module, "map_position_data"),
            "transform_positions_data": getattr(
                mapping_module, "transform_positions_data"
            ),
        }
    except (ImportError, AttributeError) as error:
        logger.error(f"Error importing broker modules: {error}")
        return None


async def get_positionbook_with_auth(
    db, auth_token: str, broker: str, original_data: Dict[str, Any] = None
) -> Tuple[bool, Dict[str, Any], int]:
    """
    Get position book details using provided auth token.

    Args:
        auth_token: Authentication token for the broker API
        broker: Name of the broker
        original_data: Original request data (for sandbox mode, optional for internal calls)

    Returns:
        Tuple containing:
        - Success status (bool)
        - Response data (dict)
        - HTTP status code (int)
    """
    # If in analyze mode AND we have original_data (API call), route to sandbox
    # If original_data is None (internal call), use live broker
    from app.core.schemas.settings_db import get_analyze_mode

    if await get_analyze_mode(db) and original_data:
        from app.core.services.sandbox_service import sandbox_get_positions

        api_key = original_data.get("apikey")
        if not api_key:
            return (
                False,
                {
                    "status": "error",
                    "message": "API key required for sandbox mode",
                    "mode": "analyze",
                },
                400,
            )

        return await sandbox_get_positions(db, api_key, original_data)

    broker_funcs = import_broker_module(broker)
    if broker_funcs is None:
        return (
            False,
            {"status": "error", "message": "Broker-specific module not found"},
            404,
        )

    try:
        # Get positions data using broker's implementation
        positions_data = broker_funcs["get_positions"](auth_token)
        if inspect.iscoroutine(positions_data) or inspect.iscoroutinefunction(
            broker_funcs["get_positions"]
        ):
            positions_data = await positions_data

        if "status" in positions_data and positions_data["status"] == "error":
            return (
                False,
                {
                    "status": "error",
                    "message": positions_data.get(
                        "message", "Error fetching positions data"
                    ),
                },
                500,
            )

        # Transform data using mapping functions
        positions_data = broker_funcs["map_position_data"](positions_data)
        positions_data = broker_funcs["transform_positions_data"](positions_data)

        # Format numeric values to 2 decimal places
        formatted_positions = format_position_data(positions_data)

        return True, {"status": "success", "data": formatted_positions}, 200
    except Exception as e:
        logger.error(f"Error processing positions data: {e}")
        traceback.print_exc()
        return False, {"status": "error", "message": str(e)}, 500


async def get_positionbook(
    db,
    api_key: Optional[str] = None,
    auth_token: Optional[str] = None,
    broker: Optional[str] = None,
) -> Tuple[bool, Dict[str, Any], int]:
    """
    Get position book details.
    Supports both API-based authentication and direct internal calls.

    Args:
        api_key: OpenAlgo API key (for API-based calls)
        auth_token: Direct broker authentication token (for internal calls)
        broker: Direct broker name (for internal calls)

    Returns:
        Tuple containing:
        - Success status (bool)
        - Response data (dict)
        - HTTP status code (int)
    """
    # Case 1: API-based authentication
    if api_key and not (auth_token and broker):
        auth_details = await get_auth_token_broker(db, api_key)
        if auth_details is None or len(auth_details) < 2:
            return False, {"status": "error", "message": "Invalid openalgo apikey"}, 403
        AUTH_TOKEN, broker_name = auth_details
        original_data = {"apikey": api_key}
        return await get_positionbook_with_auth(db, AUTH_TOKEN, broker_name, original_data)

    # Case 2: Direct internal call with auth_token and broker
    elif auth_token and broker:
        return await get_positionbook_with_auth(db, auth_token, broker, None)

    # Case 3: Invalid parameters
    else:
        return (
            False,
            {
                "status": "error",
                "message": "Either api_key or both auth_token and broker must be provided",
            },
            400,
        )
