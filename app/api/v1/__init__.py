from fastapi import APIRouter

from app.api.v1.endpoints import account, auth, search, symbol, telegram, trading

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(account.router, prefix="/account", tags=["account"])
api_router.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
api_router.include_router(trading.router, prefix="/trading", tags=["trading"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(symbol.router, prefix="/symbol", tags=["symbol"])