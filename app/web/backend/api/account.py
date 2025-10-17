from fastapi import APIRouter, Depends, HTTPException, status
from app.web.models.api_schemas import APIKeySchema, FundsResponse, OrderbookResponse, TradebookResponse, PositionbookResponse, HoldingsResponse, OpenPositionResponse, OpenPositionRequest
from app.web.services.funds_service import get_funds
from app.web.services.orderbook_service import get_orderbook
from app.web.services.tradebook_service import get_tradebook
from app.web.services.positionbook_service import get_positionbook
from app.web.services.holdings_service import get_holdings
from app.web.services.openposition_service import get_open_position, emit_analyzer_error
from app.utils.logging import logger
from app.db.apilog_db import async_log_order, executor as log_executor
from app.db.settings_db import get_analyze_mode

router = APIRouter()

# Placeholder for get_current_user dependency - assume it exists and handles authentication
async def get_current_user():
    # In a real application, this would validate a token and return a user object.
    # For this migration, we assume it's available and handles authentication.
    pass

@router.post("/funds", response_model=FundsResponse)
async def funds_endpoint(
    api_key_data: APIKeySchema,
    current_user: dict = Depends(get_current_user)
):
    """Get account funds and margin details"""
    try:
        success, response_data, status_code = await get_funds(api_key=api_key_data.apikey)
        if not success:
            raise HTTPException(status_code=status_code, detail=response_data.get("message", "An error occurred"))
        return FundsResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error in funds endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

@router.post("/orderbook", response_model=OrderbookResponse)
async def orderbook_endpoint(
    api_key_data: APIKeySchema,
    current_user: dict = Depends(get_current_user)
):
    """Get order book details"""
    try:
        success, response_data, status_code = await get_orderbook(api_key=api_key_data.apikey)
        if not success:
            raise HTTPException(status_code=status_code, detail=response_data.get("message", "An error occurred"))
        return OrderbookResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error in orderbook endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

@router.post("/tradebook", response_model=TradebookResponse)
async def tradebook_endpoint(
    api_key_data: APIKeySchema,
    current_user: dict = Depends(get_current_user)
):
    """Get trade book details"""
    try:
        success, response_data, status_code = await get_tradebook(api_key=api_key_data.apikey)
        if not success:
            raise HTTPException(status_code=status_code, detail=response_data.get("message", "An error occurred"))
        return TradebookResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error in tradebook endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

@router.post("/positionbook", response_model=PositionbookResponse)
async def positionbook_endpoint(
    api_key_data: APIKeySchema,
    current_user: dict = Depends(get_current_user)
):
    """Get position book details"""
    try:
        success, response_data, status_code = await get_positionbook(api_key=api_key_data.apikey)
        if not success:
            raise HTTPException(status_code=status_code, detail=response_data.get("message", "An error occurred"))
        return PositionbookResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error in positionbook endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

@router.post("/holdings", response_model=HoldingsResponse)
async def holdings_endpoint(
    api_key_data: APIKeySchema,
    current_user: dict = Depends(get_current_user)
):
    """Get holdings details"""
    try:
        success, response_data, status_code = await get_holdings(api_key=api_key_data.apikey)
        if not success:
            raise HTTPException(status_code=status_code, detail=response_data.get("message", "An error occurred"))
        return HoldingsResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error in holdings endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

@router.post("/openposition", response_model=OpenPositionResponse)
async def openposition_endpoint(
    open_position_request: OpenPositionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Get quantity of an open position"""
    try:
        api_key = open_position_request.apikey
        position_data = open_position_request.dict(exclude_unset=True, exclude={"apikey"})
        
        success, response_data, status_code = await get_open_position(
            position_data=position_data,
            api_key=api_key
        )
        if not success:
            if get_analyze_mode():
                # Assuming emit_analyzer_error is synchronous or handled differently in FastAPI context
                # and returns a dict compatible with HTTPException detail
                error_detail = emit_analyzer_error(open_position_request.dict(), response_data.get("message", "An error occurred"))
                raise HTTPException(status_code=status_code, detail=error_detail)
            
            log_executor.submit(async_log_order, 'openposition', open_position_request.dict(), response_data)
            raise HTTPException(status_code=status_code, detail=response_data.get("message", "An error occurred"))
        
        return OpenPositionResponse(**response_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("An unexpected error occurred in OpenPosition endpoint.")
        error_message = 'An unexpected error occurred'
        if get_analyze_mode():
            # Assuming emit_analyzer_error is synchronous or handled differently in FastAPI context
            error_detail = emit_analyzer_error(open_position_request.dict(), error_message)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_detail)
        
        log_executor.submit(async_log_order, 'openposition', open_position_request.dict(), {'status': 'error', 'message': error_message})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message)
