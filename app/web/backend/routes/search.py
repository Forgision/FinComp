from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Dict, Optional

from app.db.symbol import enhanced_search_symbols
from app.utils.session import check_session_validity_fastapi
from app.utils.logging import logger
from app.core.session import get_db
from app.web.frontend import templates

search_router = APIRouter(prefix="/search", tags=["Search"])


@search_router.get("/token", response_class=HTMLResponse)
async def token(request: Request, session_valid: bool = Depends(check_session_validity_fastapi)):
    """Route for the search form page"""
    return templates.TemplateResponse("token.html", {"request": request})

@search_router.get("/", response_class=HTMLResponse)
async def search(
    request: Request,
    symbol: str = Query("", alias="symbol"),
    exchange: Optional[str] = Query(None),
    session_valid: bool = Depends(check_session_validity_fastapi),
    db: Session = Depends(get_db)
):
    """Main search route for full results page"""
    query = symbol.strip()
    
    if not query:
        logger.info("Empty search query received")
        return templates.TemplateResponse("token.html", {"request": request, "error_message": "Please enter a search term."})
    
    logger.info(f"Searching for symbol: {query}, exchange: {exchange}")
    results = enhanced_search_symbols(db, query, exchange)
    
    if not results:
        logger.info(f"No results found for query: {query}")
        return templates.TemplateResponse("token.html", {"request": request, "error_message": "No matching symbols found."})
    
    results_dicts = [{
        'symbol': result.symbol,
        'brsymbol': result.brsymbol,
        'name': result.name,
        'exchange': result.exchange,
        'brexchange': result.brexchange,
        'token': result.token,
        'expiry': result.expiry,
        'strike': result.strike,
        'lotsize': result.lotsize,
        'instrumenttype': result.instrumenttype,
        'tick_size': result.tick_size
    } for result in results]
    
    logger.info(f"Found {len(results_dicts)} results for query: {query}")
    return templates.TemplateResponse("search.html", {"request": request, "results": results_dicts})

@search_router.get("/api/search", response_class=JSONResponse)
async def api_search(
    q: str = Query("", alias="q"),
    exchange: Optional[str] = Query(None),
    session_valid: bool = Depends(check_session_validity_fastapi),
    db: Session = Depends(get_db)
):
    """API endpoint for AJAX search suggestions"""
    query = q.strip()
    
    if not query:
        logger.debug("Empty API search query received")
        return JSONResponse({'results': []})
    
    logger.debug(f"API search for symbol: {query}, exchange: {exchange}")
    results = enhanced_search_symbols(db, query, exchange)
    results_dicts = [{
        'symbol': result.symbol,
        'brsymbol': result.brsymbol,
        'name': result.name,
        'exchange': result.exchange,
        'token': result.token
    } for result in results]
    
    logger.debug(f"API search found {len(results_dicts)} results")
    return JSONResponse({'results': results_dicts})