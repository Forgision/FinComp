from collections import OrderedDict

from app.core.security import check_session_validity_fastapi
from app.frontend import templates
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.models.tradingview_models import TradingViewRequest
from app.db.models.auth_db import get_api_key_for_tradingview
from app.db.models.session import get_db
from app.db.models.symbol import enhanced_search_symbols
from app.utils.logging import logger

host = settings.HOST_SERVER

tv_json_router = APIRouter(prefix="/tradingview", tags=["tradingview"])

@tv_json_router.get("/", response_class=Response, name="tradingview_json")
async def tradingview_json_get(request: Request, user: str = Depends(check_session_validity_fastapi)):
    return templates.TemplateResponse("tradingview.html", {"request": request, "host": host})

@tv_json_router.post("/", name="tradingview_json")
async def tradingview_json_post(
    request_body: TradingViewRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(check_session_validity_fastapi) # Renamed to avoid conflict with 'user'
):
    try:
        symbol_input = request_body.symbol
        exchange = request_body.exchange
        product = request_body.product

        logger.info(f"Processing TradingView request - Symbol: {symbol_input}, Exchange: {exchange}, Product: {product}")

        # Get actual API key for TradingView
        api_key = get_api_key_for_tradingview(db, user_data.get('user'))

        if not api_key:
            logger.error(f"API key not found for user: {user_data.get('user')}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

        # Use enhanced search function
        symbols = enhanced_search_symbols(db, symbol_input, exchange)
        if not symbols:
            logger.warning(f"Symbol not found: {symbol_input}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not found")

        symbol_data = symbols[0]  # Take the first match
        logger.info(f"Found matching symbol: {symbol_data.symbol}")

        # Create the JSON response object with OrderedDict
        json_data = OrderedDict([
            ("apikey", api_key),  # Use actual API key
            ("strategy", "Tradingview"),
            ("symbol", symbol_data.symbol),
            ("action", "{{strategy.order.action}}"),
            ("exchange", symbol_data.exchange),
            ("pricetype", "MARKET"),
            ("product", product),
            ("quantity", "{{strategy.order.contracts}}"),
            ("position_size", "{{strategy.position_size}}"),
        ])

        logger.info("Successfully generated TradingView webhook data")
        return JSONResponse(content=json_data)

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error processing TradingView request: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
