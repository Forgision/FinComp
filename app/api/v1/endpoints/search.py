from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.trading import SearchSchema
from database.auth_db import verify_api_key
from services.search_service import search_symbols as service_search_symbols
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post("/search")
async def search_symbols_endpoint(search_data: SearchSchema, request: Request, db: Session = Depends(get_db)):
    """Search for symbols in the database"""
    api_key = search_data.apikey

    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        success, response_data, status_code = service_search_symbols(
            query=search_data.query,
            exchange=search_data.exchange,
            api_key=api_key
        )
        return JSONResponse(content=response_data, status_code=status_code)
    except Exception as e:
        logger.exception("An unexpected error occurred in Search endpoint.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred in the API endpoint"
        )