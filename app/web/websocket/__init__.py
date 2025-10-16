# websocket_proxy/__init__.py

from app.utils.logging import logger

from app.web.websocket.server import WebSocketProxy, main as websocket_main
from app.web.websocket.broker_factory import register_adapter, create_broker_adapter

#TODO: register other adapters when available
# Import the angel_adapter directly from the broker directory
from app.web.broker.fyers.streaming.fyers_websocket_adapter import FyersWebSocketAdapter
from app.web.broker.angel.streaming.angel_adapter import AngelWebSocketAdapter
from app.web.broker.zerodha.streaming.zerodha_adapter import ZerodhaWebSocketAdapter
from app.web.broker.dhan.streaming.dhan_adapter import DhanWebSocketAdapter
from app.web.broker.flattrade.streaming.flattrade_adapter import FlattradeWebSocketAdapter
from app.web.broker.shoonya.streaming.shoonya_adapter import ShoonyaWebSocketAdapter
from app.web.broker.ibulls.streaming.ibulls_adapter import IbullsWebSocketAdapter
from app.web.broker.compositedge.streaming.compositedge_adapter import CompositedgeWebSocketAdapter
from app.web.broker.fivepaisaxts.streaming.fivepaisaxts_adapter import FivepaisaXTSWebSocketAdapter
from app.web.broker.iifl.streaming.iifl_adapter import IiflWebSocketAdapter
from app.web.broker.wisdom.streaming.wisdom_adapter import WisdomWebSocketAdapter
from app.web.broker.upstox.streaming.upstox_adapter import UpstoxWebSocketAdapter
from app.web.broker.kotak.streaming.kotak_adapter import KotakWebSocketAdapter
from app.web.broker.definedge.streaming.definedge_adapter import DefinedgeWebSocketAdapter

# AliceBlue adapter will be loaded dynamically

# Register adapters
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

# AliceBlue adapter will be registered dynamically when first used

# __all__ = [
#     'WebSocketProxy',
#     'websocket_main',
#     'register_adapter',
#     'create_broker_adapter',
#     'AngelWebSocketAdapter',
#     'ZerodhaWebSocketAdapter',
#     'DhanWebSocketAdapter',
#     'FlattradeWebSocketAdapter',
#     'ShoonyaWebSocketAdapter',
#     'IbullsWebSocketAdapter',
#     'CompositedgeWebSocketAdapter',
#     'FivepaisaXTSWebSocketAdapter',
#     'IiflWebSocketAdapter',
#     'JainamWebSocketAdapter',
#     'TrustlineWebSocketAdapter',
#     'WisdomWebSocketAdapter',
#     'UpstoxWebSocketAdapter',
#     'KotakWebSocketAdapter',
#     'FyersWebSocketAdapter',
#     'DefinedgeWebSocketAdapter'
# ]
