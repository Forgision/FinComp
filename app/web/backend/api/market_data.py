from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from typing import Optional
import importlib
import pandas as pd
from datetime import datetime, timezone, timedelta
import pytz
import os

from app.web.models.api_schemas import (
    QuotesSchema, HistorySchema, DepthSchema, IntervalsSchema,
    SymbolSchema, SearchSchema, ExpirySchema
)
from app.web.services.quotes_service import get_quotes
from app.web.services.history_service import get_history
from app.web.services.depth_service import get_depth
from app.web.services.intervals_service import get_intervals
from app.web.services.symbol_service import get_symbol_info
from app.web.services.search_service import search_symbols
from app.web.services.expiry_service import get_expiry_dates
from app.utils.logging import get_logger
from app.db.auth_db import get_auth_token_broker
from app.web.backend.dependencies.users import get_current_user # Assuming this dependency exists

router = APIRouter(
    prefix="/market_data",
    tags=["Market Data"],
    dependencies=[Depends(get_current_user)] # Secure all market data endpoints
)

logger = get_logger(__name__)

# --- Helper functions for Ticker endpoint (migrated from ticker.py) ---

def import_broker_module(broker_name: str):
    try:
        module_path = f'app.web.broker.{broker_name}.api.data'
        broker_module = importlib.import_module(module_path)
        return broker_module
    except ImportError as error:
        logger.exception(f"Error importing broker module '{module_path}': {error}")
        return None

def convert_timestamp(timestamp: int, interval: str):
    """Convert timestamp to appropriate format based on interval"""
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    ist = pytz.timezone('Asia/Kolkata')
    dt_ist = dt.astimezone(ist)
    
    if interval.upper() == 'D':
        return dt_ist.strftime('%Y-%m-%d')
    
    return dt_ist.strftime('%Y-%m-%d'), dt_ist.strftime('%H:%M:%S')

def validate_and_adjust_date_range(start_date: str, end_date: str, interval: str):
    """
    Validate and adjust date range based on interval to prevent large queries
    """
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        interval_upper = interval.upper()
        if interval_upper in ['D', 'W', 'M']:
            max_days = 10 * 365
        else:
            max_days = 30
        
        earliest_start = end_dt - timedelta(days=max_days)
        
        if start_dt < earliest_start:
            adjusted_start = earliest_start.strftime('%Y-%m-%d')
            logger.warning(f"Date range adjusted: {start_date} -> {adjusted_start} (interval: {interval}, max days: {max_days})")
            return adjusted_start, end_date, True
        
        return start_date, end_date, False
        
    except Exception as e:
        logger.error(f"Error in date range validation: {e}")
        return start_date, end_date, False

# --- Endpoints ---

@router.post("/quotes")
async def get_quotes_endpoint(quotes_data: QuotesSchema, current_user: dict = Depends(get_current_user)):
    """Get real-time quotes for given symbol"""
    try:
        success, response_data, status_code = await get_quotes(
            symbol=quotes_data.symbol,
            exchange=quotes_data.exchange,
            api_key=quotes_data.apikey
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception(f"Unexpected error in quotes endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

@router.post("/history")
async def get_history_endpoint(history_data: HistorySchema, current_user: dict = Depends(get_current_user)):
    """Get historical data for given symbol"""
    try:
        success, response_data, status_code = await get_history(
            symbol=history_data.symbol,
            exchange=history_data.exchange,
            interval=history_data.interval,
            start_date=history_data.start_date,
            end_date=history_data.end_date,
            api_key=history_data.apikey
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception(f"Unexpected error in history endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

@router.post("/depth")
async def get_depth_endpoint(depth_data: DepthSchema, current_user: dict = Depends(get_current_user)):
    """Get market depth for given symbol"""
    try:
        success, response_data, status_code = await get_depth(
            symbol=depth_data.symbol,
            exchange=depth_data.exchange,
            api_key=depth_data.apikey
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception(f"Unexpected error in depth endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

@router.post("/intervals")
async def get_intervals_endpoint(intervals_data: IntervalsSchema, current_user: dict = Depends(get_current_user)):
    """Get supported intervals for the broker"""
    try:
        success, response_data, status_code = await get_intervals(api_key=intervals_data.apikey)
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception(f"Unexpected error in intervals endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

@router.post("/symbol")
async def get_symbol_endpoint(symbol_data: SymbolSchema, current_user: dict = Depends(get_current_user)):
    """Get symbol information for a given symbol and exchange"""
    try:
        success, response_data, status_code = await get_symbol_info(
            symbol=symbol_data.symbol,
            exchange=symbol_data.exchange,
            api_key=symbol_data.apikey
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception(f"Unexpected error in symbol endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

@router.post("/search")
async def search_symbols_endpoint(search_data: SearchSchema, current_user: dict = Depends(get_current_user)):
    """Search for symbols in the database"""
    try:
        success, response_data, status_code = await search_symbols(
            query=search_data.query,
            exchange=search_data.exchange,
            api_key=search_data.apikey
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception(f"Unexpected error in search endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

@router.post("/expiry")
async def get_expiry_endpoint(expiry_data: ExpirySchema, current_user: dict = Depends(get_current_user)):
    """Get expiry dates for F&O symbols (futures or options) for a given underlying symbol"""
    try:
        success, response_data, status_code = await get_expiry_dates(
            symbol=expiry_data.symbol,
            exchange=expiry_data.exchange,
            instrumenttype=expiry_data.instrumenttype,
            api_key=expiry_data.apikey
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception(f"Unexpected error in expiry endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

@router.get("/ticker/{symbol_with_exchange}")
async def get_ticker_endpoint(
    symbol_with_exchange: str,
    interval: str = Query("D"),
    start_date: Optional[str] = Query(None, alias="from"),
    end_date: Optional[str] = Query(None, alias="to"),
    adjusted: Optional[bool] = Query(False),
    sort: Optional[str] = Query(None),
    apikey: str = Query(...),
    format: str = Query("json"),
    current_user: dict = Depends(get_current_user)
):
    """Get aggregate bars for a stock over a given date range with specified interval"""
    response_format = format.lower()

    try:
        parts = symbol_with_exchange.split(':')
        if len(parts) == 2:
            exchange, symbol = parts
        else:
            exchange = "NSE" # Default if not provided
            symbol = symbol_with_exchange # Assuming symbol_with_exchange is just the symbol

        ticker_data_for_validation = {
            'apikey': apikey,
            'symbol': symbol,
            'exchange': exchange,
            'interval': interval,
            'start_date': start_date,
            'end_date': end_date
        }

        # Validate request data using HistorySchema
        history_schema = HistorySchema(**ticker_data_for_validation)

        # Apply date range restrictions
        if history_schema.start_date and history_schema.end_date:
            adjusted_start, adjusted_end, was_adjusted = validate_and_adjust_date_range(
                history_schema.start_date,
                history_schema.end_date,
                history_schema.interval
            )
            history_schema.start_date = adjusted_start
            history_schema.end_date = adjusted_end
            
            if was_adjusted:
                logger.info(f"Date range restricted for {history_schema.symbol} ({history_schema.interval}): {adjusted_start} to {adjusted_end}")

        AUTH_TOKEN, broker = get_auth_token_broker(apikey)
        if AUTH_TOKEN is None:
            if response_format == 'txt':
                return PlainTextResponse("Invalid openalgo apikey\n", status_code=status.HTTP_403_FORBIDDEN)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid openalgo apikey")

        broker_module = import_broker_module(broker)
        if broker_module is None:
            if response_format == 'txt':
                return PlainTextResponse("Broker-specific module not found\n", status_code=status.HTTP_404_NOT_FOUND)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Broker-specific module not found")

        try:
            data_handler = broker_module.BrokerData(AUTH_TOKEN)
            
            df = await data_handler.get_history( # Assuming get_history is async
                history_schema.symbol,
                history_schema.exchange,
                history_schema.interval,
                history_schema.start_date,
                history_schema.end_date
            )
            
            if not isinstance(df, pd.DataFrame):
                raise ValueError("Invalid data format returned from broker")

            if response_format == 'txt':
                text_output = []
                symbol_for_output = f"{history_schema.exchange}:{history_schema.symbol}"
                
                for _, row in df.iterrows():
                    timestamp = convert_timestamp(row['timestamp'], history_schema.interval)
                    volume = int(row['volume'])
                    if history_schema.interval.upper() == 'D':
                        text_output.append(f"{symbol_for_output},{timestamp},{row['open']},{row['high']},{row['low']},{row['close']},{volume}")
                    else:
                        date, time = timestamp
                        text_output.append(f"{symbol_for_output},{date},{time},{row['open']},{row['high']},{row['low']},{row['close']},{volume}")
                
                return PlainTextResponse('\n'.join(text_output), media_type="text/plain")
            else:
                return JSONResponse(content={
                    'status': 'success',
                    'data': df.to_dict(orient='records')
                }, status_code=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Error in broker_module.get_history: {e}")
            if response_format == 'txt':
                return PlainTextResponse(str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    except Exception as e:
        logger.exception(f"Unexpected error in ticker endpoint: {e}")
        if response_format == 'txt':
            return PlainTextResponse('An unexpected error occurred', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")