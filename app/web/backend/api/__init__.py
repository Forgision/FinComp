from ..routes.auth import auth_router
from ..routes.broker_auth import broker_router
from ..routes.core import core_router
from ..routes.dashboard import dashboard_router

from .orders import orders_router
from .account import account_router
from .market_data import market_data_router
from .utility import utility_router
from .telegram import telegram_router

__all__ = ["auth_router", "broker_router", "core_router", "dashboard_router", "orders_router", "account_router", "market_data_router", "utility_router", "telegram_router"]