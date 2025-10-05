from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.account import HoldingsSchema, OpenPositionSchema, OrderbookSchema, OrderStatusSchema, PositionbookSchema, FundsSchema, IntervalsSchema, AnalyzerSchema, AnalyzerToggleSchema, PingSchema
from database.auth_db import verify_api_key
from utils.logging import get_logger
from services.holdings_service import get_holdings as service_get_holdings
from services.orderstatus_service import get_order_status as service_get_order_status
from services.positionbook_service import get_positionbook as service_get_positionbook
from services.funds_service import get_funds as service_get_funds
from services.openposition_service import get_open_position as service_get_open_position
from services.orderbook_service import get_orderbook_data as service_get_orderbook_data
from services.intervals_service import get_intervals as service_get_intervals
from services.analyzer_service import get_analyzer_status as service_get_analyzer_status
from services.analyzer_service import toggle_analyzer_mode as service_toggle_analyzer_mode
from services.ping_service import get_ping as service_get_ping

logger = get_logger(__name__)

router = APIRouter()

@router.post("/holdings")
async def get_holdings(holdings_data: HoldingsSchema, request: Request, db: Session = Depends(get_db)):
    """Get holdings for a given API key"""
    api_key = holdings_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        success, response_data, status_code = service_get_holdings(
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in Holdings endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )

@router.post("/orderstatus")
async def get_orderstatus(orderstatus_data: OrderStatusSchema, request: Request, db: Session = Depends(get_db)):
    """Get status of a specific order"""
    api_key = orderstatus_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        success, response_data, status_code = service_get_order_status(
            status_data=orderstatus_data.model_dump(exclude_unset=True),
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in OrderStatus endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )

@router.post("/positionbook")
async def get_positionbook_data(positionbook_data: PositionbookSchema, request: Request, db: Session = Depends(get_db)):
    """Get position book details"""
    api_key = positionbook_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        success, response_data, status_code = service_get_positionbook(
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in Positionbook endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )

@router.post("/funds")
async def get_funds_data(funds_data: FundsSchema, request: Request, db: Session = Depends(get_db)):
    """Get account funds and margin details"""
    api_key = funds_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        success, response_data, status_code = service_get_funds(
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in Funds endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )

@router.post("/openposition")
async def get_open_position_data(position_data: OpenPositionSchema, request: Request, db: Session = Depends(get_db)):
    """Get quantity of an open position"""
    api_key = position_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

@router.post("/orderbook")
async def get_orderbook_data(orderbook_data: OrderbookSchema, request: Request, db: Session = Depends(get_db)):
    """Get order book details"""
    api_key = orderbook_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
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

@router.post("/intervals")
async def get_intervals_data(intervals_data: IntervalsSchema, request: Request, db: Session = Depends(get_db)):
    """Get supported intervals for the broker"""
    api_key = intervals_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        from services.intervals_service import get_intervals as service_get_intervals
        
        success, response_data, status_code = service_get_intervals(
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in Intervals endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
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

@router.post("/analyzer")
async def get_analyzer_status_data(analyzer_data: AnalyzerSchema, request: Request, db: Session = Depends(get_db)):
    """Get analyzer mode status and statistics"""
    api_key = analyzer_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        from services.analyzer_service import get_analyzer_status as service_get_analyzer_status
        
        success, response_data, status_code = service_get_analyzer_status(
            analyzer_data=analyzer_data.model_dump(exclude_unset=True),
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in Analyzer status endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )

@router.post("/analyzer/toggle")
async def toggle_analyzer_mode_data(analyzer_data: AnalyzerToggleSchema, request: Request, db: Session = Depends(get_db)):
    """Toggle analyzer mode on/off"""
    api_key = analyzer_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        from services.analyzer_service import toggle_analyzer_mode as service_toggle_analyzer_mode
        
        success, response_data, status_code = service_toggle_analyzer_mode(
            analyzer_data=analyzer_data.model_dump(exclude_unset=True),
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in Analyzer toggle endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )

@router.post("/ping")
async def get_ping_data(ping_data: PingSchema, request: Request, db: Session = Depends(get_db)):
    """Check API connectivity and authentication"""
    api_key = ping_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        from services.ping_service import get_ping as service_get_ping
        
        success, response_data, status_code = service_get_ping(
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in Ping endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )