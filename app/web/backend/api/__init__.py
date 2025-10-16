from ..routes.auth import auth_router
from ..routes.broker_auth import broker_router
from ..routes.core import core_router
from ..routes.dashboard import dashboard_router

__all__ = ["auth_router", "broker_router", "core_router", "dashboard_router"]