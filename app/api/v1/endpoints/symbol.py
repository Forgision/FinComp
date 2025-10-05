from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.trading import SymbolSchema
from database.auth_db import verify_api_key
from services.symbol_service import get_symbol_info as service_get_symbol_info
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post("/symbol")
async def get_symbol_info_endpoint(symbol_data: SymbolSchema, request: Request, db: Session = Depends(get_db)):
    """Get symbol information for a given symbol and exchange"""
    api_key = symbol_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        success, response_data, status_code = service_get_symbol_info(
            symbol=symbol_data.symbol,
            exchange=symbol_data.exchange,
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in Symbol endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )