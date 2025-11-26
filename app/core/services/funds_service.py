import importlib
import traceback
from typing import Any, Dict, Optional, Tuple

from app.core.schemas.auth_db import get_auth_token_broker
from sqlalchemy.ext.asyncio import AsyncSession

# Initialize logger
from app.utils.logging import logger


def import_broker_module(broker_name: str) -> Optional[Any]:
    """
    Dynamically import the broker-specific funds module.

    Args:
        broker_name: Name of the broker

    Returns:
        The imported module or None if import fails
    """
    module_path = None
    try:
        module_path = f"app.web.broker.broker.{broker_name}.api.funds"
        broker_module = importlib.import_module(module_path)
        return broker_module
    except ImportError as error:
        logger.error(f"Error importing broker module '{module_path}': {error}")
        return None


async def get_funds_with_auth(
    db: AsyncSession,
    auth_token: str,
    broker: str,
    original_data: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Dict[str, Any], int]:
    """
    Get account funds and margin details from the broker using provided auth token.

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
    from app.core.schemas.settings_db import get_analyze_mode

    if await get_analyze_mode(db) and original_data:
        from app.core.services.sandbox_service import sandbox_get_funds

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

        return await sandbox_get_funds(db, api_key, original_data)

    broker_module = import_broker_module(broker)
    if broker_module is None:
        return (
            False,
            {"status": "error", "message": "Broker-specific module not found"},
            404,
        )

    try:
        # Get funds data using broker's implementation
        funds = broker_module.get_margin_data(auth_token)

        return True, {"status": "success", "data": funds}, 200
    except Exception as e:
        logger.error(f"Error in broker_module.get_margin_data: {e}")
        traceback.print_exc()
        return False, {"status": "error", "message": str(e)}, 500


async def get_funds(
    db: AsyncSession,
    api_key: Optional[str] = None,
    auth_token: Optional[str] = None,
    broker: Optional[str] = None,
) -> Tuple[bool, Dict[str, Any], int]:
    """
    Get account funds and margin details from the broker.
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
        auth_details = get_auth_token_broker(db, provided_api_key=api_key)
        if not auth_details or len(auth_details) < 2:
            return False, {"status": "error", "message": "Invalid openalgo apikey"}, 403
        AUTH_TOKEN, broker_name = auth_details[0], auth_details[1]
        if AUTH_TOKEN is None or broker_name is None:
            return False, {"status": "error", "message": "Invalid openalgo apikey"}, 403
        original_data = {"apikey": api_key}
        return await get_funds_with_auth(db, AUTH_TOKEN, broker_name, original_data)

    # Case 2: Direct internal call with auth_token and broker
    elif auth_token and broker:
        return await get_funds_with_auth(db, auth_token, broker)

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
