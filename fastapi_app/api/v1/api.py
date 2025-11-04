from fastapi import APIRouter
from fastapi_app.api.v1.endpoints import test, account, orders, websocket, frontend

api_router = APIRouter()
api_router.include_router(test.router, prefix="/test", tags=["test"])
api_router.include_router(account.router, prefix="/account", tags=["Account"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
api_router.include_router(frontend.router, tags=["Frontend"])
