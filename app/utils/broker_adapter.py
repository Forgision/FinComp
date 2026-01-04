import importlib
import functools
from typing import Any, Dict, Optional
from app.utils.logging import logger

@functools.lru_cache(maxsize=128)
def get_broker_funcs(broker_name: str, service_type: str) -> Optional[Dict[str, Any]]:
    """
    Dynamically import the broker-specific modules and return the required functions.
    This function is cached to avoid repeated imports and attribute lookups.

    Args:
        broker_name: Name of the broker
        service_type: Type of service ('holdings', 'positions', 'tradebook', 'orderbook')

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

        if service_type == "holdings":
            return {
                "get_holdings": getattr(api_module, "get_holdings"),
                "map_portfolio_data": getattr(mapping_module, "map_portfolio_data"),
                "calculate_portfolio_statistics": getattr(
                    mapping_module, "calculate_portfolio_statistics"
                ),
                "transform_holdings_data": getattr(
                    mapping_module, "transform_holdings_data"
                ),
            }
        elif service_type == "positions":
            return {
                "get_positions": getattr(api_module, "get_positions"),
                "map_position_data": getattr(mapping_module, "map_position_data"),
                "transform_positions_data": getattr(
                    mapping_module, "transform_positions_data"
                ),
            }
        elif service_type == "tradebook":
            return {
                "get_trade_book": getattr(api_module, "get_trade_book"),
                "map_trade_data": getattr(mapping_module, "map_trade_data"),
                "transform_tradebook_data": getattr(
                    mapping_module, "transform_tradebook_data"
                ),
            }
        elif service_type == "orderbook":
            return {
                "get_order_book": getattr(api_module, "get_order_book"),
                "map_order_data": getattr(mapping_module, "map_order_data"),
                "calculate_order_statistics": getattr(
                    mapping_module, "calculate_order_statistics"
                ),
                "transform_order_data": getattr(mapping_module, "transform_order_data"),
            }
        else:
            logger.error(f"Unknown service type: {service_type}")
            return None

    except (ImportError, AttributeError) as error:
        logger.error(f"Error importing broker modules for {broker_name}: {error}")
        return None
