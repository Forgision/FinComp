import importlib
from typing import Dict, Optional, Type

from app.utils.logging import logger
from .base_adapter import BaseBrokerWebSocketAdapter

# Registry of all supported broker adapters
BROKER_ADAPTERS: Dict[str, Type[BaseBrokerWebSocketAdapter]] = {}


def register_adapter(
    broker_name: str, adapter_class: Type[BaseBrokerWebSocketAdapter]
) -> None:
    """
    Register a broker adapter class for a specific broker

    Args:
        broker_name: Name of the broker
        adapter_class: Class that implements the BaseBrokerWebSocketAdapter interface
    """
    BROKER_ADAPTERS[broker_name.lower()] = adapter_class


def create_broker_adapter(broker_name: str) -> Optional[BaseBrokerWebSocketAdapter]:
    """
    Create an instance of the appropriate broker adapter

    Args:
        broker_name: Name of the broker (e.g., 'angel', 'zerodha')

    Returns:
        BaseBrokerWebSocketAdapter: An instance of the appropriate broker adapter

    Raises:
        ValueError: If the broker is not supported
    """
    broker_name = broker_name.lower()

    # Check if adapter is registered
    if broker_name in BROKER_ADAPTERS:
        logger.info(f"Creating adapter for broker: {broker_name}")
        return BROKER_ADAPTERS[broker_name]()

    # Try dynamic import if not registered
    try:
        # Try to import from broker-specific directory first
        module_name = (
            f"app.web.broker.broker.{broker_name}.streaming.{broker_name}_adapter"
        )
        class_name = f"{broker_name.capitalize()}WebSocketAdapter"

        try:
            # Import the module
            module = importlib.import_module(module_name)

            # Get the adapter class
            adapter_class = getattr(module, class_name)

            # Register the adapter for future use
            register_adapter(broker_name, adapter_class)

            # Create and return an instance
            return adapter_class()
        except (ImportError, AttributeError) as e:
            logger.warning(f"Could not import from broker-specific path: {e}")

            # Try websocket_proxy directory as fallback
            module_name = f"app.websocket.{broker_name}_adapter"

            # Import the module
            module = importlib.import_module(module_name)

            # Get the adapter class
            adapter_class = getattr(module, class_name)

            # Register the adapter for future use
            register_adapter(broker_name, adapter_class)

            # Create and return an instance
            return adapter_class()

    except (ImportError, AttributeError) as e:
        logger.exception(f"Failed to load adapter for broker {broker_name}: {e}")
        raise ValueError(f"Unsupported broker: {broker_name}. No adapter available.")

    return None


def register_all_adapters():
    from app.web.brokers.angel.streaming.angel_adapter import AngelWebSocketAdapter
    from app.web.brokers.compositedge.streaming.compositedge_adapter import (
        CompositedgeWebSocketAdapter,
    )
    from app.web.brokers.definedge.streaming.definedge_adapter import (
        DefinedgeWebSocketAdapter,
    )
    from app.web.brokers.dhan.streaming.dhan_adapter import DhanWebSocketAdapter
    from app.web.brokers.fivepaisaxts.streaming.fivepaisaxts_adapter import (
        FivepaisaXTSWebSocketAdapter,
    )
    from app.web.brokers.flattrade.streaming.flattrade_adapter import (
        FlattradeWebSocketAdapter,
    )
    from app.web.brokers.fyers.streaming.fyers_websocket_adapter import (
        FyersWebSocketAdapter,
    )
    from app.web.brokers.ibulls.streaming.ibulls_adapter import IbullsWebSocketAdapter
    from app.web.brokers.iifl.streaming.iifl_adapter import IiflWebSocketAdapter
    from app.web.brokers.kotak.streaming.kotak_adapter import KotakWebSocketAdapter
    from app.web.brokers.shoonya.streaming.shoonya_adapter import (
        ShoonyaWebSocketAdapter,
    )
    from app.web.brokers.upstox.streaming.upstox_adapter import UpstoxWebSocketAdapter
    from app.web.brokers.wisdom.streaming.wisdom_adapter import WisdomWebSocketAdapter
    from app.web.brokers.zerodha.streaming.zerodha_adapter import (
        ZerodhaWebSocketAdapter,
    )
    from app.web.broker.broker.dummy_broker.streaming.dummy_broker_adapter import (
        DummyBrokerWebSocketAdapter,
    )

    register_adapter("fyers", FyersWebSocketAdapter)
    register_adapter("angel", AngelWebSocketAdapter)
    register_adapter("zerodha", ZerodhaWebSocketAdapter)
    register_adapter("dhan", DhanWebSocketAdapter)
    register_adapter("flattrade", FlattradeWebSocketAdapter)
    register_adapter("shoonya", ShoonyaWebSocketAdapter)
    register_adapter("ibulls", IbullsWebSocketAdapter)
    register_adapter("compositedge", CompositedgeWebSocketAdapter)
    register_adapter("fivepaisaxts", FivepaisaXTSWebSocketAdapter)
    register_adapter("iifl", IiflWebSocketAdapter)
    register_adapter("wisdom", WisdomWebSocketAdapter)
    register_adapter("upstox", UpstoxWebSocketAdapter)
    register_adapter("kotak", KotakWebSocketAdapter)
    register_adapter("definedge", DefinedgeWebSocketAdapter)
    register_adapter("dummy_broker", DummyBrokerWebSocketAdapter)
