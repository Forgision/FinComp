import json
import queue
import re
import threading
import time as time_module
import uuid
from collections import deque
from datetime import datetime, time

import pytz
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.utils.logging import logger
from app.utils.session import check_session_validity_fastapi
from app.db.auth_db import get_api_key_for_tradingview
from app.db.strategy_db import (
    Strategy, StrategySymbolMapping, bulk_add_symbol_mappings, create_strategy,
    delete_strategy, delete_symbol_mapping, get_all_strategies, get_strategy,
    get_strategy_by_webhook_id, get_symbol_mappings, get_user_strategies,
    toggle_strategy, update_strategy_times
)
from app.db.symbol import enhanced_search_symbols
from app.web.frontend import templates
from app.core.config import settings

# Rate limiting configuration (placeholders for now, will integrate slowapi if needed)
WEBHOOK_RATE_LIMIT = settings.WEBHOOK_RATE_LIMIT
STRATEGY_RATE_LIMIT = settings.STRATEGY_RATE_LIMIT

strategy_router = APIRouter(prefix="/strategy", tags=["Strategy"])

# Initialize scheduler for time-based controls
scheduler = BackgroundScheduler(
    timezone=pytz.timezone('Asia/Kolkata'),
    job_defaults={
        'coalesce': True,
        'misfire_grace_time': 300,
        'max_instances': 1
    }
)
scheduler.start()

# Get base URL from environment or default to localhost
BASE_URL = settings.HOST_SERVER # TODO: Update this to reflect FastAPI server URL

# Valid exchanges
VALID_EXCHANGES = ['NSE', 'BSE', 'NFO', 'CDS', 'BFO', 'BCD', 'MCX', 'NCDEX']

# Product types per exchange
EXCHANGE_PRODUCTS = {
    'NSE': ['MIS', 'CNC'],
    'BSE': ['MIS', 'CNC'],
    'NFO': ['MIS', 'NRML'],
    'CDS': ['MIS', 'NRML'],
    'BFO': ['MIS', 'NRML'],
    'BCD': ['MIS', 'NRML'],
    'MCX': ['MIS', 'NRML'],
    'NCDEX': ['MIS', 'NRML']
}

# Default values
DEFAULT_EXCHANGE = 'NSE'
DEFAULT_PRODUCT = 'MIS'

# Separate queues for different order types
regular_order_queue = queue.Queue()  # For placeorder (up to 10/sec)
smart_order_queue = queue.Queue()    # For placesmartorder (1/sec)

# Order processor state
order_processor_running = False
order_processor_lock = threading.Lock()

# Rate limiting state for regular orders
last_regular_orders = deque(maxlen=10)  # Track last 10 regular order timestamps

def process_orders():
    """Background task to process orders from both queues with rate limiting"""
    global order_processor_running
    
    while True:
        try:
            # Process smart orders first (1 per second)
            try:
                smart_order = smart_order_queue.get_nowait()
                if smart_order is None:  # Poison pill
                    break
                
                try:
                    response = requests.post(f'{BASE_URL}/api/v1/placesmartorder', json=smart_order['payload'])
                    if response.ok:
                        logger.info(f'Smart order placed for {smart_order["payload"]["symbol"]} in strategy {smart_order["payload"]["strategy"]}')
                    else:
                        logger.error(f'Error placing smart order for {smart_order["payload"]["symbol"]}: {response.text}')
                except Exception as e:
                    logger.error(f'Error placing smart order: {str(e)}')
                
                # Always wait 1 second after smart order
                time_module.sleep(1)
                continue  # Start next iteration
                
            except queue.Empty:
                pass  # No smart orders, continue to regular orders
            
            # Process regular orders (up to 10 per second)
            now = time_module.time() # Changed to time_module.time() to avoid conflict with datetime.time
            
            # Clean up old timestamps
            while last_regular_orders and now - last_regular_orders[0] > 1:
                last_regular_orders.popleft()
            
            # Process regular orders if under rate limit
            if len(last_regular_orders) < 10:
                try:
                    regular_order = regular_order_queue.get_nowait()
                    if regular_order is None:  # Poison pill
                        break
                    
                    try:
                        response = requests.post(f'{BASE_URL}/api/v1/placeorder', json=regular_order['payload'])
                        if response.ok:
                            logger.info(f'Regular order placed for {regular_order["payload"]["symbol"]} in strategy {regular_order["payload"]["strategy"]}')
                            last_regular_orders.append(now)
                        else:
                            logger.error(f'Error placing regular order for {regular_order["payload"]["symbol"]}: {response.text}')
                    except Exception as e:
                        logger.error(f'Error placing regular order: {str(e)}')
                    
                except queue.Empty:
                    pass  # No regular orders
            
            # Small sleep to prevent CPU spinning
            time_module.sleep(0.1)
            
        except Exception as e:
            logger.error(f'Error in order processor: {str(e)}')
            time_module.sleep(1)  # Sleep on error to prevent rapid retries

def ensure_order_processor():
    """Ensure the order processor is running"""
    global order_processor_running
    with order_processor_lock:
        if not order_processor_running:
            threading.Thread(target=process_orders, daemon=True).start()
            order_processor_running = True

def queue_order(endpoint: str, payload: dict):
    """Add order to appropriate queue"""
    ensure_order_processor()
    if endpoint == 'placesmartorder':
        smart_order_queue.put({'payload': payload})
    else:
        regular_order_queue.put({'payload': payload})

def validate_strategy_times(start_time_str: str, end_time_str: str, squareoff_time_str: str):
    """Validate strategy time settings"""
    try:
        if not all([start_time_str, end_time_str, squareoff_time_str]):
            return False, "All time fields are required"
        
        # Convert strings to time objects for comparison
        start = datetime.strptime(start_time_str, '%H:%M').time()
        end = datetime.strptime(end_time_str, '%H:%M').time()
        squareoff = datetime.strptime(squareoff_time_str, '%H:%M').time()
        
        # Market hours validation (9:15 AM to 3:30 PM)
        market_open = datetime.strptime('09:15', '%H:%M').time()
        market_close = datetime.strptime('15:30', '%H:%M').time()
        
        if start < market_open:
            return False, "Start time cannot be before market open (9:15)"
        if end > market_close:
            return False, "End time cannot be after market close (15:30)"
        if squareoff > market_close:
            return False, "Square off time cannot be after market close (15:30)"
        if start >= end:
            return False, "Start time must be before end time"
        if squareoff < start:
            return False, "Square off time must be after start time"
        if squareoff < end:
            return False, "Square off time must be after end time"
        
        return True, None
        
    except ValueError:
        return False, "Invalid time format. Use HH:MM format"

def validate_strategy_name(name: str):
    """Validate strategy name format"""
    if not name:
        return False, "Strategy name is required"
    
    # Check length
    if len(name) < 3 or len(name) > 50:
        return False, "Strategy name must be between 3 and 50 characters"
    
    # Check characters
    if not re.match(r'^[A-Za-z0-9\s\-_]+$', name):
        return False, "Strategy name can only contain letters, numbers, spaces, hyphens and underscores"
    
    return True, None

def schedule_squareoff(strategy_id: int, db: Session):
    """Schedule squareoff for intraday strategy"""
    strategy = get_strategy(db, strategy_id)
    if not strategy or not strategy.is_intraday or not strategy.squareoff_time:
        return
    
    try:
        hours, minutes = map(int, strategy.squareoff_time.split(':'))
        job_id = f'squareoff_{strategy_id}'
        
        # Remove existing job if any
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
        
        # Add new job
        scheduler.add_job(
            squareoff_positions,
            'cron',
            hour=hours,
            minute=minutes,
            args=[strategy_id, db], # Pass db session to the job
            id=job_id,
            timezone=pytz.timezone('Asia/Kolkata')
        )
        logger.info(f'Scheduled squareoff for strategy {strategy_id} at {hours}:{minutes}')
    except Exception as e:
        logger.error(f'Error scheduling squareoff for strategy {strategy_id}: {str(e)}')

def squareoff_positions(strategy_id: int, db: Session):
    """Square off all positions for intraday strategy"""
    try:
        strategy = get_strategy(db, strategy_id)
        if not strategy or not strategy.is_intraday:
            return
        
        # Get API key for authentication
        api_key = get_api_key_for_tradingview(db, strategy.user_id)
        if not api_key:
            logger.error(f'No API key found for strategy {strategy_id}')
            return
            
        # Get all symbol mappings
        mappings = get_symbol_mappings(db, strategy_id)
        
        for mapping in mappings:
            # Use placesmartorder with quantity=0 and position_size=0 for squareoff
            payload = {
                'apikey': api_key,
                'symbol': mapping.symbol,
                'exchange': mapping.exchange,
                'product': mapping.product_type,
                'strategy': strategy.name,
                'action': 'SELL',  # Direction doesn't matter for closing
                'pricetype': 'MARKET',
                'quantity': '0',
                'position_size': '0',  # This will close the position
                'price': '0',
                'trigger_price': '0',
                'disclosed_quantity': '0'
            }
            
            # Queue the order instead of executing directly
            queue_order('placesmartorder', payload)
            
    except Exception as e:
        logger.error(f'Error in squareoff_positions for strategy {strategy_id}: {str(e)}')

@strategy_router.get("/", response_class=HTMLResponse)
async def index(request: Request, user_id: str = Depends(check_session_validity_fastapi), db: Session = Depends(get_db)):
    """List all strategies"""
    try:
        logger.info(f"Fetching strategies for user: {user_id}")
        strategies = get_user_strategies(db, user_id)
        return templates.TemplateResponse(
            "strategy/index.html", {"request": request, "strategies": strategies, "user_id": user_id}
        )
    except HTTPException:
        raise # Re-raise HTTPException from dependency
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        # In FastAPI, we raise HTTPException directly instead of flash and redirect
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error loading strategies"
        )

@strategy_router.get("/new", response_class=HTMLResponse)
async def new_strategy_get(request: Request, user_id: str = Depends(check_session_validity_fastapi)):
    """Display form to create new strategy"""
    return templates.TemplateResponse("strategy/new_strategy.html", {"request": request, "user_id": user_id})

@strategy_router.post("/new", response_class=RedirectResponse)
async def new_strategy_post(
    request: Request,
    platform: str = Form(...),
    name: str = Form(...),
    strategy_type: str = Form(...),
    trading_mode: str = Form("LONG"),
    start_time: str = Form(None),
    end_time: str = Form(None),
    squareoff_time: str = Form(None),
    user_id: str = Depends(check_session_validity_fastapi),
    db: Session = Depends(get_db)
):
    """Create new strategy"""
    try:
        if not user_id:
            logger.error("No user_id found in session")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please login again."
            )
        
        logger.info(f"Creating strategy for user: {user_id}")

        # Validate platform
        if not platform:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please select a platform"
            )

        # Create prefixed strategy name
        full_name = f"{platform}_{name.strip()}"

        # Validate strategy name
        is_valid_name, name_error = validate_strategy_name(full_name)
        if not is_valid_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=name_error
            )
        
        # Validate times for intraday strategy
        is_intraday = strategy_type == 'intraday'
        if is_intraday:
            is_valid_time, time_error = validate_strategy_times(start_time, end_time, squareoff_time)
            if not is_valid_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=time_error
                )
        else:
            start_time = end_time = squareoff_time = None
        
        # Generate webhook ID
        webhook_id = str(uuid.uuid4())
        
        # Create strategy with user ID
        strategy = create_strategy(
            db=db,
            name=full_name,
            webhook_id=webhook_id,
            user_id=user_id,
            is_intraday=is_intraday,
            trading_mode=trading_mode,
            start_time=start_time,
            end_time=end_time,
            squareoff_time=squareoff_time,
            platform=platform
        )
        
        if strategy:
            if strategy.is_intraday:
                schedule_squareoff(strategy.id, db)
            return RedirectResponse(
                url=strategy_router.url_path_for("configure_symbols", strategy_id=strategy.id),
                status_code=status.HTTP_302_FOUND
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating strategy"
            )
            
    except HTTPException:
        raise # Re-raise HTTPException from dependency or above
    except Exception as e:
        logger.error(f'Error creating strategy: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating strategy"
        )

@strategy_router.get("/{strategy_id}", response_class=HTMLResponse)
async def view_strategy(request: Request, strategy_id: int, user_id: str = Depends(check_session_validity_fastapi), db: Session = Depends(get_db)):
    """View strategy details"""
    strategy = get_strategy(db, strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    if strategy.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized access"
        )
    
    symbol_mappings = get_symbol_mappings(db, strategy_id)
    
    return templates.TemplateResponse(
        "strategy/view_strategy.html",
        {"request": request, "strategy": strategy, "symbol_mappings": symbol_mappings, "user_id": user_id}
    )

@strategy_router.post("/toggle/{strategy_id}", response_class=RedirectResponse)
async def toggle_strategy_route(strategy_id: int, user_id: str = Depends(check_session_validity_fastapi), db: Session = Depends(get_db)):
    """Toggle strategy active status"""
    try:
        strategy = toggle_strategy(db, strategy_id)
        if strategy:
            if strategy.is_active:
                # Schedule squareoff if being activated
                schedule_squareoff(strategy_id, db)
            else:
                # Remove squareoff job if being deactivated
                try:
                    scheduler.remove_job(f'squareoff_{strategy_id}')
                except Exception:
                    pass
            
            return RedirectResponse(
                url=strategy_router.url_path_for("view_strategy", strategy_id=strategy_id),
                status_code=status.HTTP_302_FOUND
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Error toggling strategy: Strategy not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Error toggling strategy: {str(e)}'
        )

@strategy_router.post("/{strategy_id}/delete", response_class=JSONResponse)
async def delete_strategy_route(strategy_id: int, user_id: str = Depends(check_session_validity_fastapi), db: Session = Depends(get_db)):
    """Delete strategy"""
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired"
        )
        
    strategy = get_strategy(db, strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Check if strategy belongs to user
    if strategy.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized"
        )
    
    try:
        # Remove squareoff job if exists
        try:
            scheduler.remove_job(f'squareoff_{strategy_id}')
        except Exception:
            pass
            
        if delete_strategy(db, strategy_id):
            return JSONResponse(content={'status': 'success'})
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete strategy"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Error deleting strategy {strategy_id}: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@strategy_router.get("/{strategy_id}/configure", response_class=HTMLResponse)
async def configure_symbols_get(request: Request, strategy_id: int, user_id: str = Depends(check_session_validity_fastapi), db: Session = Depends(get_db)):
    """Display form to configure symbols for strategy"""
    strategy = get_strategy(db, strategy_id)
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    
    if strategy.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access")
    
    symbol_mappings = get_symbol_mappings(db, strategy_id)
    return templates.TemplateResponse(
        "strategy/configure_symbols.html",
        {
            "request": request,
            "strategy": strategy,
            "symbol_mappings": symbol_mappings,
            "exchanges": VALID_EXCHANGES,
            "user_id": user_id
        }
    )

@strategy_router.post("/{strategy_id}/configure", response_class=JSONResponse)
async def configure_symbols_post(request: Request, strategy_id: int, user_id: str = Depends(check_session_validity_fastapi), db: Session = Depends(get_db)):
    """Configure symbols for strategy"""
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please login again."
        )
        
    strategy = get_strategy(db, strategy_id)
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    
    # Check if strategy belongs to user
    if strategy.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access")
    
    try:
        # Get data from either JSON or form
        if request.headers.get('content-type') == 'application/json':
            data = await request.json()
        else:
            form_data = await request.form()
            data = form_data._dict # Access the underlying dictionary
        
        logger.info(f"Received data: {data}")
        
        # Handle bulk symbols
        if 'symbols' in data:
            symbols_text = data.get('symbols')
            mappings = []
            
            for line in symbols_text.strip().split('\n'):
                if not line.strip():
                    continue
                
                parts = line.strip().split(',')
                if len(parts) != 4:
                    raise ValueError(f'Invalid format in line: {line}')
                
                symbol, exchange, quantity, product = parts
                if exchange not in VALID_EXCHANGES:
                    raise ValueError(f'Invalid exchange: {exchange}')
                
                mappings.append({
                    'symbol': symbol.strip(),
                    'exchange': exchange.strip(),
                    'quantity': int(quantity),
                    'product_type': product.strip()
                })
            
            if mappings:
                bulk_add_symbol_mappings(db, strategy_id, mappings)
                return JSONResponse(content={'status': 'success'})
        
        # Handle single symbol
        else:
            symbol = data.get('symbol')
            exchange = data.get('exchange')
            quantity = data.get('quantity')
            product_type = data.get('product_type')
            
            logger.info(f"Processing single symbol: symbol={symbol}, exchange={exchange}, quantity={quantity}, product_type={product_type}")
            
            if not all([symbol, exchange, quantity, product_type]):
                missing = []
                if not symbol: missing.append('symbol')
                if not exchange: missing.append('exchange')
                if not quantity: missing.append('quantity')
                if not product_type: missing.append('product_type')
                raise ValueError(f'Missing required fields: {", ".join(missing)}')
            
            if exchange not in VALID_EXCHANGES:
                raise ValueError(f'Invalid exchange: {exchange}')
            
            try:
                quantity = int(quantity)
            except ValueError:
                raise ValueError('Quantity must be a valid number')
            
            if quantity <= 0:
                raise ValueError('Quantity must be greater than 0')
            
            mapping = add_symbol_mapping(
                db=db,
                strategy_id=strategy_id,
                symbol=symbol,
                exchange=exchange,
                quantity=quantity,
                product_type=product_type
            )
            
            if mapping:
                return JSONResponse(content={'status': 'success'})
            else:
                raise ValueError('Failed to add symbol mapping')
            
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error configuring symbols: {error_msg}')
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

@strategy_router.post("/{strategy_id}/symbol/{mapping_id}/delete", response_class=JSONResponse)
async def delete_symbol(strategy_id: int, mapping_id: int, user_id: str = Depends(check_session_validity_fastapi), db: Session = Depends(get_db)):
    """Delete symbol mapping"""
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired"
        )
        
    strategy = get_strategy(db, strategy_id)
    if not strategy or strategy.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found or unauthorized"
        )
    
    try:
        if delete_symbol_mapping(db, mapping_id):
            return JSONResponse(content={'status': 'success'})
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Symbol mapping not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Error deleting symbol mapping: {str(e)}')
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@strategy_router.get("/search", response_class=JSONResponse)
async def search_symbols(request: Request, q: str = "", exchange: str = None, user_id: str = Depends(check_session_validity_fastapi), db: Session = Depends(get_db)):
    """Search symbols endpoint"""
    if not q:
        return JSONResponse(content={'results': []})
    
    results = enhanced_search_symbols(db, q.strip(), exchange)
    return JSONResponse(content={
        'results': [{
            'symbol': result.symbol,
            'name': result.name,
            'exchange': result.exchange
        } for result in results]
    })

@strategy_router.post("/webhook/{webhook_id}", response_class=JSONResponse)
async def webhook(webhook_id: str, request: Request, db: Session = Depends(get_db)):
    """Handle webhook from trading platform"""
    try:
        strategy = get_strategy_by_webhook_id(db, webhook_id)
        if not strategy:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Invalid webhook ID')
        
        if not strategy.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Strategy is inactive')
        
        data = await request.json()
        if not data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No data received')

        # Check trading hours for intraday strategies
        if strategy.is_intraday:
            now = datetime.now(pytz.timezone('Asia/Kolkata'))
            current_time = now.strftime('%H:%M')
            
            # Determine if this is an entry or exit order
            action = data.get('action', '').upper()
            position_size = int(data.get('position_size', 0))
            
            is_exit_order = False
            if strategy.trading_mode == 'LONG':
                is_exit_order = action == 'SELL'
            elif strategy.trading_mode == 'SHORT':
                is_exit_order = action == 'BUY'
            else:  # BOTH mode
                is_exit_order = position_size == 0
            
            # For entry orders, check if within entry time window
            if not is_exit_order:
                if strategy.start_time and current_time < strategy.start_time:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Entry orders not allowed before start time')
                
                if strategy.end_time and current_time > strategy.end_time:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Entry orders not allowed after end time')
            
            # For exit orders, check if within exit time window (up to square off time)
            else:
                if strategy.start_time and current_time < strategy.start_time:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Exit orders not allowed before start time')
                
                if strategy.squareoff_time and current_time > strategy.squareoff_time:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Exit orders not allowed after square off time')
        
        # Validate required fields
        required_fields = ['symbol', 'action']
        if strategy.trading_mode == 'BOTH':
            required_fields.append('position_size')
            
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Missing required fields: {", ".join(missing_fields)}')
            
        # Validate action based on trading mode
        action = data['action'].upper()
        position_size = int(data.get('position_size', 0))
        
        if strategy.trading_mode == 'LONG':
            if action not in ['BUY', 'SELL']:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid action for LONG mode. Use BUY to enter, SELL to exit')
            use_smart_order = action == 'SELL'
        elif strategy.trading_mode == 'SHORT':
            if action not in ['BUY', 'SELL']:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid action for SHORT mode. Use SELL to enter, BUY to exit')
            use_smart_order = action == 'BUY'
        else:  # BOTH mode
            if action not in ['BUY', 'SELL']:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid action. Use BUY or SELL')
            
            # Validate position size based on action
            if action == 'BUY' and position_size < 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='For BUY orders in BOTH mode, position_size must be >= 0')
            if action == 'SELL' and position_size > 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='For SELL orders in BOTH mode, position_size must be <= 0')
            
            # Smart order logic:
            # - BUY with position_size=0 means exit SHORT position
            # - SELL with position_size=0 means exit LONG position
            use_smart_order = position_size == 0
            
        # Get symbol mapping
        mapping = next((m for m in get_symbol_mappings(db, strategy.id) if m.symbol == data['symbol']), None)
        if not mapping:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'No mapping found for symbol {data["symbol"]}')
            
        # Get API key from database
        api_key = get_api_key_for_tradingview(db, strategy.user_id)
        if not api_key:
            logger.error(f'No API key found for user {strategy.user_id}')
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='No API key found')

        # Prepare order payload
        payload = {
            'apikey': api_key,
            'symbol': mapping.symbol,
            'exchange': mapping.exchange,
            'product': mapping.product_type,
            'strategy': strategy.name,
            'action': action,
            'pricetype': 'MARKET'
        }
        
        # Set quantity based on order type
        if strategy.trading_mode == 'BOTH':
            # For BOTH mode, always use placesmartorder with direct position size
            # Set quantity to 0 if position_size is 0 (for exits)
            quantity = '0' if position_size == 0 else str(mapping.quantity)
            payload.update({
                'quantity': quantity,
                'position_size': str(position_size),  # Use position_size directly from webhook data
                'price': '0',
                'trigger_price': '0',
                'disclosed_quantity': '0'
            })
            endpoint = 'placesmartorder'
        else:
            # For LONG/SHORT modes, keep existing logic
            if use_smart_order:
                payload.update({
                    'quantity': '0',
                    'position_size': '0',  # This will close the position
                    'price': '0',
                    'trigger_price': '0',
                    'disclosed_quantity': '0'
                })
                endpoint = 'placesmartorder'
            else:
                # For regular orders, use absolute value of position_size if provided, otherwise use mapping quantity
                quantity = abs(position_size) if position_size != 0 else mapping.quantity
                payload.update({
                    'quantity': str(quantity)
                })
                endpoint = 'placeorder'
            
        # Queue the order
        queue_order(endpoint, payload)
        return JSONResponse(content={'message': f'Order queued successfully for {data["symbol"]}'}, status_code=status.HTTP_200_OK)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Error processing webhook: {str(e)}')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Internal server error')