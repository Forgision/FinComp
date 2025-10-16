"""
FastAPI router for WebSocket service layer, providing internal UI components
and real-time market data without authentication overhead.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.utils.session import check_session_validity_fastapi
from app.utils.web.socketio import sio
from app.web.services.websocket_service import (
    get_websocket_status,
    get_websocket_subscriptions,
    subscribe_to_symbols,
    unsubscribe_from_symbols,
    unsubscribe_all,
    get_market_data
)
from app.web.services.market_data_service import (
    get_market_data_service,
    subscribe_to_market_updates,
    unsubscribe_from_market_updates
)
from app.utils.logging import logger
from app.db.auth_db import get_api_key_for_tradingview
from app.web.frontend import templates


# Create FastAPI router
websocket_router = APIRouter(prefix="/websocket", tags=["WebSocket"])

# Helper to get username from session
async def get_username_from_session_fastapi(request: Request) -> Optional[str]:
    """Get username from current session"""
    username = request.session.get("user")
    if username:
        logger.info(f"Debug: username='{username}'")
        api_key = await get_api_key_for_tradingview(username)
        logger.info(f"Debug: API key found for username '{username}': {bool(api_key)}")
        return username
    else:
        logger.warning("Debug: No username in session")
    return None

@websocket_router.get("/dashboard")
async def websocket_dashboard(request: Request, username: str = Depends(check_session_validity_fastapi)):
    """Render WebSocket dashboard for testing"""
    return templates.TemplateResponse("websocket/dashboard.html", {"request": request})

@websocket_router.get("/test")
async def websocket_test(request: Request, username: str = Depends(check_session_validity_fastapi)):
    """Render WebSocket test page for RELIANCE and TCS"""
    return templates.TemplateResponse("websocket/test_market_data.html", {"request": request})

# REST endpoints for UI (no additional auth needed - page is already protected)
@websocket_router.get("/api/websocket/status")
async def api_websocket_status(username: str = Depends(get_username_from_session_fastapi)):
    """Get WebSocket connection status for current user"""
    if not username:
        return JSONResponse(content={
            'status': 'error',
            'message': 'Session not found - please refresh page',
            'connected': False,
            'authenticated': False
        }, status_code=200)

    success, data, status_code = await get_websocket_status(username)
    return JSONResponse(content=data, status_code=status_code)

@websocket_router.get("/api/websocket/subscriptions")
async def api_websocket_subscriptions(username: str = Depends(get_username_from_session_fastapi)):
    """Get current subscriptions for current user"""
    if not username:
        return JSONResponse(content={
            'status': 'error',
            'message': 'Session not found - please refresh page',
            'subscriptions': []
        }, status_code=200)

    success, data, status_code = await get_websocket_subscriptions(username)
    return JSONResponse(content=data, status_code=status_code)

@websocket_router.post("/api/websocket/subscribe")
async def api_websocket_subscribe(request: Request, username: str = Depends(get_username_from_session_fastapi)):
    """Subscribe to symbols for current user"""
    if not username:
        return JSONResponse(content={'status': 'error', 'message': 'Session not found - please refresh page'}, status_code=200)

    data = await request.json()
    symbols = data.get('symbols', [])
    mode = data.get('mode', 'Quote')
    broker = data.get('broker')

    success, result, status_code = await subscribe_to_symbols(username, broker, symbols, mode)
    return JSONResponse(content=result, status_code=status_code)

@websocket_router.post("/api/websocket/unsubscribe")
async def api_websocket_unsubscribe(request: Request, username: str = Depends(get_username_from_session_fastapi)):
    """Unsubscribe from symbols for current user"""
    if not username:
        return JSONResponse(content={'status': 'error', 'message': 'Session not found - please refresh page'}, status_code=200)

    data = await request.json()
    symbols = data.get('symbols', [])
    mode = data.get('mode', 'Quote')
    broker = data.get('broker')

    success, result, status_code = await unsubscribe_from_symbols(username, broker, symbols, mode)
    return JSONResponse(content=result, status_code=status_code)

@websocket_router.post("/api/websocket/unsubscribe-all")
async def api_websocket_unsubscribe_all(request: Request, username: str = Depends(get_username_from_session_fastapi)):
    """Unsubscribe from all symbols for current user"""
    if not username:
        return JSONResponse(content={'status': 'error', 'message': 'Session not found - please refresh page'}, status_code=200)

    data = await request.json() if request.headers.get('content-type') == 'application/json' else {}
    broker = data.get('broker')

    success, result, status_code = await unsubscribe_all(username, broker)
    return JSONResponse(content=result, status_code=status_code)

@websocket_router.get("/api/websocket/market-data")
async def api_websocket_market_data(
    symbol: str,
    exchange: str,
    username: str = Depends(get_username_from_session_fastapi)
):
    """Get cached market data"""
    if not username:
        return JSONResponse(content={'status': 'error', 'message': 'Session not found - please refresh page'}, status_code=200)

    success, data, status_code = await get_market_data(username, symbol, exchange)
    return JSONResponse(content=data, status_code=status_code)

@websocket_router.get("/api/websocket/apikey")
async def api_get_websocket_apikey(username: str = Depends(get_username_from_session_fastapi)):
    """Get API key for WebSocket authentication"""
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Session not found - please refresh page')

    api_key = await get_api_key_for_tradingview(username)

    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No API key found. Please generate an API key first.')

    return JSONResponse(content={'status': 'success', 'api_key': api_key}, status_code=200)

@websocket_router.get("/api/websocket/config")
async def api_get_websocket_config(request: Request, username: str = Depends(get_username_from_session_fastapi)):
    """Get WebSocket configuration including URL"""
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Session not found - please refresh page')

    websocket_url = settings.WEBSOCKET_URL

    if request.url.scheme == 'https' and websocket_url.startswith('ws://'):
        websocket_url = websocket_url.replace('ws://', 'wss://')
        logger.info(f"Upgraded WebSocket URL to secure: {websocket_url}")

    return JSONResponse(content={
        'status': 'success',
        'websocket_url': websocket_url,
        'is_secure': request.url.scheme == 'https',
        'original_url': settings.WEBSOCKET_URL
    }, status_code=200)

# Socket.IO events for real-time updates
@sio.on('connect', namespace='/market')
async def handle_connect(sid: str, environ: Dict[str, Any], auth: Optional[Dict[str, Any]]):
    """Handle client connection"""
    session = await sio.get_session(sid)
    username = session.get('user')

    if not username:
        return False  # Reject connection

    sio.enter_room(sid, f'user_{username}', namespace='/market')
    await sio.emit('connected', {'status': 'Connected to market data stream'}, room=sid, namespace='/market')
    logger.info(f"User {username} connected to market data stream (SID: {sid})")
    return True

@sio.on('disconnect', namespace='/market')
async def handle_disconnect(sid: str):
    """Handle client disconnection"""
    session = await sio.get_session(sid)
    username = session.get('user')

    if username:
        sio.leave_room(sid, f'user_{username}', namespace='/market')
        logger.info(f"User {username} disconnected from market data stream (SID: {sid})")

@sio.on('subscribe', namespace='/market')
async def handle_subscribe(sid: str, data: Dict[str, Any]):
    """Handle subscription request via Socket.IO"""
    session = await sio.get_session(sid)
    username = session.get('user')

    if not username:
        await sio.emit('error', {'message': 'Not authenticated'}, room=sid, namespace='/market')
        return

    symbols = data.get('symbols', [])
    mode = data.get('mode', 'Quote')
    broker = data.get('broker')

    success, result, _ = await subscribe_to_symbols(username, broker, symbols, mode)

    if success:
        await sio.emit('subscription_success', result, room=sid, namespace='/market')
    else:
        await sio.emit('subscription_error', result, room=sid, namespace='/market')

@sio.on('unsubscribe', namespace='/market')
async def handle_unsubscribe(sid: str, data: Dict[str, Any]):
    """Handle unsubscription request via Socket.IO"""
    session = await sio.get_session(sid)
    username = session.get('user')

    if not username:
        await sio.emit('error', {'message': 'Not authenticated'}, room=sid, namespace='/market')
        return

    symbols = data.get('symbols', [])
    mode = data.get('mode', 'Quote')
    broker = data.get('broker')

    success, result, _ = await unsubscribe_from_symbols(username, broker, symbols, mode)

    if success:
        await sio.emit('unsubscription_success', result, room=sid, namespace='/market')
    else:
        await sio.emit('unsubscription_error', result, room=sid, namespace='/market')

@sio.on('get_ltp', namespace='/market')
async def handle_get_ltp(sid: str, data: Dict[str, Any]):
    """Get LTP for a symbol"""
    symbol = data.get('symbol')
    exchange = data.get('exchange')

    if not symbol or not exchange:
        await sio.emit('error', {'message': 'Symbol and exchange are required'}, room=sid, namespace='/market')
        return

    market_service = get_market_data_service()
    ltp_data = market_service.get_ltp(symbol, exchange)

    await sio.emit('ltp_data', {
        'symbol': symbol,
        'exchange': exchange,
        'data': ltp_data
    }, room=sid, namespace='/market')

@sio.on('get_quote', namespace='/market')
async def handle_get_quote(sid: str, data: Dict[str, Any]):
    """Get quote for a symbol"""
    symbol = data.get('symbol')
    exchange = data.get('exchange')

    if not symbol or not exchange:
        await sio.emit('error', {'message': 'Symbol and exchange are required'}, room=sid, namespace='/market')
        return

    market_service = get_market_data_service()
    quote_data = market_service.get_quote(symbol, exchange)

    await sio.emit('quote_data', {
        'symbol': symbol,
        'exchange': exchange,
        'data': quote_data
    }, room=sid, namespace='/market')

@sio.on('get_depth', namespace='/market')
async def handle_get_depth(sid: str, data: Dict[str, Any]):
    """Get market depth for a symbol"""
    symbol = data.get('symbol')
    exchange = data.get('exchange')

    if not symbol or not exchange:
        await sio.emit('error', {'message': 'Symbol and exchange are required'}, room=sid, namespace='/market')
        return

    market_service = get_market_data_service()
    depth_data = market_service.get_market_depth(symbol, exchange)

    await sio.emit('depth_data', {
        'symbol': symbol,
        'exchange': exchange,
        'data': depth_data
    }, room=sid, namespace='/market')

# Example usage in other parts of the application
async def example_usage():
    """
    Example of how to use the WebSocket service layer in other parts of the app
    """
    # Example 1: Subscribe to symbols for a user
    user_id = 123
    symbols = [
        {'symbol': 'RELIANCE', 'exchange': 'NSE'},
        {'symbol': 'TCS', 'exchange': 'NSE'}
    ]
    success, result, status_code = await subscribe_to_symbols(user_id, 'zerodha', symbols, 'Quote')

    # Example 2: Get LTP directly from cache
    market_service = get_market_data_service()
    ltp = market_service.get_ltp('RELIANCE', 'NSE')

    # Example 3: Subscribe to updates
    def my_callback(data):
        print(f"Received update: {data}")

    subscriber_id = subscribe_to_market_updates('ltp', my_callback, {'NSE:RELIANCE', 'NSE:TCS'})

    # Example 4: Get market data for a user
    success, data, status_code = await get_market_data(user_id, 'RELIANCE', 'NSE')