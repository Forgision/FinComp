from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.trading import OrderSchema, SmartOrderSchema, ModifyOrderSchema, CancelOrderSchema, ClosePositionSchema, CancelAllOrderSchema, BasketOrderItemSchema, BasketOrderSchema, SplitOrderSchema, DepthSchema, QuotesSchema, HistorySchema
from app.schemas.account import OpenPositionSchema, HoldingsSchema, OrderbookSchema
from database.auth_db import verify_api_key
from database.auth_db import verify_api_key
from services.place_order_service import place_order as service_place_order
from services.modify_order_service import modify_order as service_modify_order
from services.cancel_order_service import cancel_order as service_cancel_order
from services.cancel_all_order_service import cancel_all_orders as service_cancel_all_orders
from services.place_smart_order_service import place_smart_order as service_place_smart_order
from services.close_position_service import close_position as service_close_position
from services.openposition_service import get_open_position as service_get_open_position
from services.quotes_service import get_quotes as service_get_quotes
from services.history_service import get_history as service_get_history
from services.depth_service import get_depth as service_get_depth
from services.orderbook_service import get_orderbook_data as service_get_orderbook_data
from services.split_order_service import split_order as service_split_order
from utils.logging import get_logger
import os

logger = get_logger(__name__)

router = APIRouter()

ORDER_RATE_LIMIT = os.getenv("ORDER_RATE_LIMIT", "10 per second") # This will be handled by a middleware later

@router.post("/place_order")
async def place_new_order(order_data: OrderSchema, request: Request, db: Session = Depends(get_db)):
    """Place an order with the broker"""
    api_key = order_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

    try:
        success, response_data, status_code = service_place_order(
            order_data=order_data.model_dump(exclude_unset=True),
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in PlaceOrder endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )

@router.post("/modify_order")
async def modify_existing_order(order_data: ModifyOrderSchema, request: Request, db: Session = Depends(get_db)):
    """Modify an existing order"""
    api_key = order_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        success, response_data, status_code = service_modify_order(
            order_data=order_data.model_dump(exclude_unset=True),
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in ModifyOrder endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )

@router.post("/cancel_order")
async def cancel_existing_order(order_data: CancelOrderSchema, request: Request, db: Session = Depends(get_db)):
    """Cancel an existing order"""
    api_key = order_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        success, response_data, status_code = service_cancel_order(
            orderid=order_data.orderid,
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in CancelOrder endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )

@router.post("/cancel_all_orders")
async def cancel_all_open_orders(order_data: CancelAllOrderSchema, request: Request, db: Session = Depends(get_db)):
    """Cancel all open orders"""
    api_key = order_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        success, response_data, status_code = service_cancel_all_orders(
            order_data=order_data.model_dump(exclude_unset=True),
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in CancelAllOrder endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )

@router.post("/place_smart_order")
async def place_smart_new_order(order_data: SmartOrderSchema, request: Request, db: Session = Depends(get_db)):
    """Place a smart order"""
    api_key = order_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        success, response_data, status_code = service_place_smart_order(
            order_data=order_data.model_dump(exclude_unset=True),
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in PlaceSmartOrder endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )

@router.post("/close_position")
async def close_open_position(position_data: ClosePositionSchema, request: Request, db: Session = Depends(get_db)):
    """Close all open positions"""
    api_key = position_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        success, response_data, status_code = service_close_position(
            position_data=position_data.model_dump(exclude_unset=True),
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in ClosePosition endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )

@router.post("/open_position")
async def get_open_position_quantity(position_data: OpenPositionSchema, request: Request, db: Session = Depends(get_db)):
    """Get quantity of an open position"""
    api_key = position_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        success, response_data, status_code = service_get_open_position(
            position_data=position_data.model_dump(exclude_unset=True),
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in OpenPosition endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )

@router.post("/quotes")
async def get_realtime_quotes(quotes_data: QuotesSchema, request: Request, db: Session = Depends(get_db)):
    """Get real-time quotes for given symbol"""
    api_key = quotes_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        success, response_data, status_code = service_get_quotes(
            symbol=quotes_data.symbol,
            exchange=quotes_data.exchange,
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in Quotes endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )

@router.post("/history")
async def get_historical_data(history_data: HistorySchema, request: Request, db: Session = Depends(get_db)):
    """Get historical data for given symbol"""
    api_key = history_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        success, response_data, status_code = service_get_history(
            symbol=history_data.symbol,
            exchange=history_data.exchange,
            interval=history_data.interval,
            start_date=history_data.start_date,
            end_date=history_data.end_date,
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in History endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )

@router.post("/depth")
async def get_market_depth(depth_data: DepthSchema, request: Request, db: Session = Depends(get_db)):
    """Get market depth for given symbol"""
    api_key = depth_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        success, response_data, status_code = service_get_depth(
            symbol=depth_data.symbol,
            exchange=depth_data.exchange,
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in Depth endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )
    
@router.post("/orderbook")
async def get_orderbook(orderbook_data: OrderbookSchema, request: Request, db: Session = Depends(get_db)):
    """
    Retrieves orderbook data for a given user.
    """
    api_key = orderbook_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

@router.post("/split_order")
async def split_large_order(split_data: SplitOrderSchema, request: Request, db: Session = Depends(get_db)):
    """Split a large order into multiple orders of specified size"""
    api_key = split_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        from services.split_order_service import split_order as service_split_order
        
        success, response_data, status_code = service_split_order(
            split_data=split_data.model_dump(exclude_unset=True),
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in SplitOrder endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )
    
    try:
        success, response_data, status_code = service_get_orderbook_data(
            api_key=api_key,
            order_data=orderbook_data.model_dump(exclude_unset=True)
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in Orderbook endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )