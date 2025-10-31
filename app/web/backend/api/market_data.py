import importlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
import pytz
from app.utils.session import check_session_validity_fastapi
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, PlainTextResponse

from app.core.models.api_schemas import (
    DepthSchema,
    ExpirySchema,
    HistorySchema,
    IntervalsSchema,
    QuotesSchema,
    SearchSchema,
    SymbolSchema,
)
from app.core.models.error_models import BaseErrorResponse
from app.core.services.depth_service import get_depth
from app.core.services.expiry_service import get_expiry_dates
from app.core.services.history_service import get_history
from app.core.services.intervals_service import get_intervals
from app.core.services.quotes_service import get_quotes
from app.core.services.search_service import search_symbols
from app.core.services.symbol_service import get_symbol_info
from app.core.models.auth_db import get_auth_token_broker
from app.utils.logging import logger

market_data_router = APIRouter(
    prefix="/market_data",
    tags=["Market Data"],
    dependencies=[Depends(check_session_validity_fastapi)] # Secure all market data endpoints
)


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

@market_data_router.post("/quotes", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def get_quotes_endpoint(quotes_data: QuotesSchema, current_user: dict = Depends(check_session_validity_fastapi)):
    """
    Get real-time quotes for a given symbol.

    Args:
        quotes_data: The request model containing the symbol, exchange, and API key.
        current_user: The current authenticated user.

    Returns:
        A JSON response with the real-time quote data.

    Raises:
        HTTPException: If an error occurs while fetching the quotes.
    """
    try:
        success, response_data, status_code = await get_quotes(
            symbol=quotes_data.symbol,
            exchange=quotes_data.exchange,
            api_key=quotes_data.apikey
        )
        if not success:
            raise HTTPException(status_code=status_code, detail=BaseErrorResponse(message=response_data.get("message", "An error occurred")).model_dump())
        return JSONResponse(content=response_data, status_code=status_code)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error in quotes endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=BaseErrorResponse(message="An unexpected error occurred").model_dump())

@market_data_router.post("/history", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def get_history_endpoint(history_data: HistorySchema, current_user: dict = Depends(check_session_validity_fastapi)):
    """
    Get historical data for a given symbol.

    Args:
        history_data: The request model containing the symbol, exchange, interval, date range, and API key.
        current_user: The current authenticated user.

    Returns:
        A JSON response with the historical data.

    Raises:
        HTTPException: If an error occurs while fetching the historical data.
    """
    try:
        success, response_data, status_code = await get_history(
            symbol=history_data.symbol,
            exchange=history_data.exchange,
            interval=history_data.interval,
            start_date=history_data.start_date,
            end_date=history_data.end_date,
            api_key=history_data.apikey
        )
        if not success:
            raise HTTPException(status_code=status_code, detail=BaseErrorResponse(message=response_data.get("message", "An error occurred")).model_dump())
        return JSONResponse(content=response_data, status_code=status_code)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error in history endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=BaseErrorResponse(message="An unexpected error occurred").model_dump())

@market_data_router.post("/depth", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def get_depth_endpoint(depth_data: DepthSchema, current_user: dict = Depends(check_session_validity_fastapi)):
    """
    Get market depth for a given symbol.

    Args:
        depth_data: The request model containing the symbol, exchange, and API key.
        current_user: The current authenticated user.

    Returns:
        A JSON response with the market depth data.

    Raises:
        HTTPException: If an error occurs while fetching the market depth.
    """
    try:
        success, response_data, status_code = await get_depth(
            symbol=depth_data.symbol,
            exchange=depth_data.exchange,
            api_key=depth_data.apikey
        )
        if not success:
            raise HTTPException(status_code=status_code, detail=BaseErrorResponse(message=response_data.get("message", "An error occurred")).model_dump())
        return JSONResponse(content=response_data, status_code=status_code)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error in depth endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=BaseErrorResponse(message="An unexpected error occurred").model_dump())

@market_data_router.post("/intervals", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def get_intervals_endpoint(intervals_data: IntervalsSchema, current_user: dict = Depends(check_session_validity_fastapi)):
    """
    Get supported intervals for the broker.

    Args:
        intervals_data: The request model containing the API key.
        current_user: The current authenticated user.

    Returns:
        A JSON response with the supported intervals.

    Raises:
        HTTPException: If an error occurs while fetching the intervals.
    """
    try:
        success, response_data, status_code = await get_intervals(api_key=intervals_data.apikey)
        if not success:
            raise HTTPException(status_code=status_code, detail=BaseErrorResponse(message=response_data.get("message", "An error occurred")).model_dump())
        return JSONResponse(content=response_data, status_code=status_code)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error in intervals endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=BaseErrorResponse(message="An unexpected error occurred").model_dump())

@market_data_router.post("/symbol", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def get_symbol_endpoint(symbol_data: SymbolSchema, current_user: dict = Depends(check_session_validity_fastapi)):
    """
    Get symbol information for a given symbol and exchange.

    Args:
        symbol_data: The request model containing the symbol, exchange, and API key.
        current_user: The current authenticated user.

    Returns:
        A JSON response with the symbol information.

    Raises:
        HTTPException: If an error occurs while fetching the symbol information.
    """
    try:
        success, response_data, status_code = await get_symbol_info(
            symbol=symbol_data.symbol,
            exchange=symbol_data.exchange,
            api_key=symbol_data.apikey
        )
        if not success:
            raise HTTPException(status_code=status_code, detail=BaseErrorResponse(message=response_data.get("message", "An error occurred")).model_dump())
        return JSONResponse(content=response_data, status_code=status_code)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error in symbol endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=BaseErrorResponse(message="An unexpected error occurred").model_dump())

@market_data_router.post("/search", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def search_symbols_endpoint(search_data: SearchSchema, current_user: dict = Depends(check_session_validity_fastapi)):
    """
    Search for symbols in the database.

    Args:
        search_data: The request model containing the search query, exchange, and API key.
        current_user: The current authenticated user.

    Returns:
        A JSON response with the search results.

    Raises:
        HTTPException: If an error occurs during the search.
    """
    try:
        success, response_data, status_code = await search_symbols(
            query=search_data.query,
            exchange=search_data.exchange,
            api_key=search_data.apikey
        )
        if not success:
            raise HTTPException(status_code=status_code, detail=BaseErrorResponse(message=response_data.get("message", "An error occurred")).model_dump())
        return JSONResponse(content=response_data, status_code=status_code)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error in search endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=BaseErrorResponse(message="An unexpected error occurred").model_dump())

@market_data_router.post("/expiry", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def get_expiry_endpoint(expiry_data: ExpirySchema, current_user: dict = Depends(check_session_validity_fastapi)):
    """
    Get expiry dates for F&O symbols (futures or options) for a given underlying symbol.

    Args:
        expiry_data: The request model containing the symbol, exchange, instrument type, and API key.
        current_user: The current authenticated user.

    Returns:
        A JSON response with the expiry dates.

    Raises:
        HTTPException: If an error occurs while fetching the expiry dates.
    """
    try:
        success, response_data, status_code = await get_expiry_dates(
            symbol=expiry_data.symbol,
            exchange=expiry_data.exchange,
            instrumenttype=expiry_data.instrumenttype,
            api_key=expiry_data.apikey
        )
        if not success:
            raise HTTPException(status_code=status_code, detail=BaseErrorResponse(message=response_data.get("message", "An error occurred")).model_dump())
        return JSONResponse(content=response_data, status_code=status_code)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error in expiry endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=BaseErrorResponse(message="An unexpected error occurred").model_dump())

@market_data_router.get("/ticker/{symbol_with_exchange}", responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": BaseErrorResponse}})
async def get_ticker_endpoint(
    symbol_with_exchange: str,
    interval: str = Query("D"),
    start_date: Optional[str] = Query(None, alias="from"),
    end_date: Optional[str] = Query(None, alias="to"),
    adjusted: Optional[bool] = Query(False),
    sort: Optional[str] = Query(None),
    apikey: str = Query(...),
    format: str = Query("json"),
    current_user: dict = Depends(check_session_validity_fastapi)
):
    """
    Get aggregate bars for a stock over a given date range with a specified interval.

    This endpoint retrieves historical aggregate data (bars) for a given stock symbol.
    It supports various intervals and allows specifying a date range. The response
    format can be either JSON or plain text.

    Args:
        symbol_with_exchange: The stock symbol, optionally prefixed with the exchange (e.g., "NSE:SBIN"). Defaults to NSE if not provided.
        interval: The data interval (e.g., "D" for daily).
        start_date: The start date for the data range (YYYY-MM-DD).
        end_date: The end date for the data range (YYYY-MM-DD).
        adjusted: Whether to return adjusted data.
        sort: The sort order for the data.
        apikey: The user's API key.
        format: The response format ("json" or "txt").
        current_user: The current authenticated user.

    Returns:
        A JSON or plain text response containing the aggregate bars data.

    Raises:
        HTTPException: If an error occurs while fetching the data, or if the API key is invalid.
    """
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
                return PlainTextResponse(BaseErrorResponse(message="Invalid openalgo apikey").model_dump_json(), status_code=status.HTTP_403_FORBIDDEN)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=BaseErrorResponse(message="Invalid openalgo apikey").model_dump())

        broker_module = import_broker_module(broker)
        if broker_module is None:
            if response_format == 'txt':
                return PlainTextResponse(BaseErrorResponse(message="Broker-specific module not found").model_dump_json(), status_code=status.HTTP_404_NOT_FOUND)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=BaseErrorResponse(message="Broker-specific module not found").model_dump())

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
                return PlainTextResponse(BaseErrorResponse(message=str(e)).model_dump_json(), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=BaseErrorResponse(message=str(e)).model_dump())

    except Exception as e:
        logger.exception(f"Unexpected error in ticker endpoint: {e}")
        if response_format == 'txt':
            return PlainTextResponse(BaseErrorResponse(message="An unexpected error occurred").model_dump_json(), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=BaseErrorResponse(message="An unexpected error occurred").model_dump())
