from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, time
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
import httpx
import os
import uuid
import time as time_module
import queue
import threading
from collections import deque

from app.db.session import get_db
from app.utils.session import check_session_validity_fastapi
from app.db.auth_db import get_api_key_for_tradingview
from app.db.chartink_db import (
    create_strategy, add_symbol_mapping, get_strategy_by_webhook_id,
    get_symbol_mappings, get_all_strategies, delete_strategy,
    update_strategy_times, delete_symbol_mapping, bulk_add_symbol_mappings,
    toggle_strategy, get_strategy, get_user_strategies
)
from app.db.symbol import enhanced_search_symbols
from app.web.frontend import templates
from app.utils.logger import logger
from app.core.config import settings


# Rate limiting configuration (FastAPI rate limiting will be handled by slowapi, this is for internal logic)
WEBHOOK_RATE_LIMIT = settings.WEBHOOK_RATE_LIMIT
STRATEGY_RATE_LIMIT = settings.STRATEGY_RATE_LIMIT

chartink_router = APIRouter(prefix="/chartink", tags=["chartink"])

# Initialize scheduler for time-based controls
scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Kolkata'))
scheduler.start()

# Get base URL from environment or default to localhost
BASE_URL = settings.HOST_SERVER or 'http://localhost:8000'

# Valid exchanges
VALID_EXCHANGES = ['NSE', 'BSE']

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
                    # Use httpx.Client for synchronous call in a thread
                    with httpx.Client() as client:
                        response = client.post(f'{BASE_URL}/api/v1/placesmartorder', json=smart_order['payload'])
                    if response.is_success:
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
            now = time_module.time()
            
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
                        # Use httpx.Client for synchronous call in a thread
                        with httpx.Client() as client:
                            response = client.post(f'{BASE_URL}/api/v1/placeorder', json=regular_order['payload'])
                        if response.is_success:
                            logger.info(f'Regular order placed for {regular_order["payload"]["symbol"]} in strategy {regular_order["payload"]["strategy"]}')
                            last_regular_orders.append(now)
                        else:
                            logger.error(f'Error placing regular order for {regular_order["payload"]["symbol"]}: {response.text}')
                    except Exception as e:
                        logger.error(f'Error placing regular order: {str(e)}')
                        
                except queue.Empty:
                    time_module.sleep(0.1)  # No orders to process
            else:
                # Rate limit hit, wait until next second
                time_module.sleep(0.1)
                
        except Exception as e:
            logger.error(f'Error in order processor: {str(e)}')
            time_module.sleep(0.1)  # Prevent tight loop on error
    
    with order_processor_lock:
        order_processor_running = False

def ensure_order_processor():
    """Ensure order processor is running"""
    global order_processor_running
    
    with order_processor_lock:
        if not order_processor_running:
            order_processor_running = True
            thread = threading.Thread(target=process_orders, daemon=True)
            thread.start()

def queue_order(endpoint, payload):
    """Add order to appropriate processing queue"""
    ensure_order_processor()
    
    if endpoint == 'placesmartorder':
        smart_order_queue.put({'endpoint': endpoint, 'payload': payload})
    else:  # placeorder
        regular_order_queue.put({'endpoint': endpoint, 'payload': payload})

def validate_strategy_times(start_time, end_time, squareoff_time):
    """Validate strategy time settings"""
    try:
        start = datetime.strptime(start_time, '%H:%M').time()
        end = datetime.strptime(end_time, '%H:%M').time()
        squareoff = datetime.strptime(squareoff_time, '%H:%M').time()
        
        if start >= end:
            return False, 'Start time must be before end time'
        if end >= squareoff:
            return False, 'End time must be before square off time'
        
        return True, None
    except ValueError:
        return False, 'Invalid time format'

def validate_strategy_name(name):
    """Validate strategy name format"""
    if not name:
        return False, 'Strategy name is required'
    
    # Add prefix if not present
    if not name.startswith('chartink_'):
        name = f'chartink_{name}'
    
    # Check for valid characters
    if not all(c.isalnum() or c in ['-', '_', ' '] for c in name.replace('chartink_', '')):
        return False, 'Strategy name can only contain letters, numbers, spaces, hyphens and underscores'
    
    return True, name

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
            args=[strategy_id],
            id=job_id,
            timezone=pytz.timezone('Asia/Kolkata')
        )
        logger.info(f'Scheduled squareoff for strategy {strategy_id} at {hours}:{minutes}')
    except Exception as e:
        logger.error(f'Error scheduling squareoff for strategy {strategy_id}: {str(e)}')

def squareoff_positions(strategy_id: int):
    """Square off all positions for intraday strategy"""
    try:
        # Need a new session for background task
        db = next(get_db())
        strategy = get_strategy(db, strategy_id)
        if not strategy or not strategy.is_intraday:
            db.close()
            return
        
        # Get API key for authentication
        api_key = get_api_key_for_tradingview(db, strategy.user_id)
        if not api_key:
            logger.error(f'No API key found for strategy {strategy_id}')
            db.close()
            return
            
        # Get all symbol mappings
        mappings = get_symbol_mappings(db, strategy_id)
        
        for mapping in mappings:
            # Use placesmartorder with quantity=0 and position_size=0 for squareoff
            payload = {
                'apikey': api_key,
                'strategy': strategy.name,
                'symbol': mapping.chartink_symbol,
                'exchange': mapping.exchange,
                'action': 'SELL',  # Direction doesn't matter for closing
                'product': mapping.product_type,
                'pricetype': 'MARKET',
                'quantity': '0',
                'position_size': '0',  # This will close the position
                'price': '0',
                'trigger_price': '0',
                'disclosed_quantity': '0'
            }
            
            # Queue the order instead of executing directly
            queue_order('placesmartorder', payload)
        db.close()
            
    except Exception as e:
        logger.error(f'Error in squareoff_positions for strategy {strategy_id}: {str(e)}')

@chartink_router.get('/')
async def index(request: Request, user_id: str = Depends(check_session_validity_fastapi), db: Session = Depends(get_db)):
    """List all strategies"""
    if not user_id:
        return RedirectResponse(url=request.url_for('auth.login'))
        
    strategies = get_user_strategies(db, user_id)  # Get only user's strategies
    return templates.TemplateResponse('chartink/index.html', {"request": request, "strategies": strategies})

@chartink_router.get('/new')
async def new_strategy_get(request: Request, user_id: str = Depends(check_session_validity_fastapi)):
    if not user_id:
        return RedirectResponse(url=request.url_for('auth.login'))
    return templates.TemplateResponse('chartink/new_strategy.html', {"request": request})

@chartink_router.post('/new')
async def new_strategy_post(
    request: Request,
    name: str = Form(...),
    type: str = Form(...),
    start_time: str = Form(None),
    end_time: str = Form(None),
    squareoff_time: str = Form(None),
    user_id: str = Depends(check_session_validity_fastapi),
    db: Session = Depends(get_db)
):
    """Create new strategy"""
    if not user_id:
        logger.error("No user_id found in session")
        return RedirectResponse(url=request.url_for('auth.login'))
    
    try:
        # Validate strategy name
        name = name.strip()
        is_valid_name, name_result = validate_strategy_name(name)
        if not is_valid_name:
            logger.error(name_result)
            return templates.TemplateResponse('chartink/new_strategy.html', {"request": request, "error": name_result})
        name = name_result  # Use the validated and prefixed name
        
        is_intraday = (type == 'intraday')
        
        if is_intraday:
            if not all([start_time, end_time, squareoff_time]):
                logger.error('All time fields are required for intraday strategy')
                return templates.TemplateResponse('chartink/new_strategy.html', {"request": request, "error": 'All time fields are required for intraday strategy'})
            
            # Validate time settings
            is_valid, error_msg = validate_strategy_times(start_time, end_time, squareoff_time)
            if not is_valid:
                logger.error(error_msg)
                return templates.TemplateResponse('chartink/new_strategy.html', {"request": request, "error": error_msg})
        
        # Generate unique webhook ID
        webhook_id = str(uuid.uuid4())
        
        # Create strategy with user ID
        strategy = create_strategy(
            db=db,
            name=name,
            webhook_id=webhook_id,
            user_id=user_id,
            is_intraday=is_intraday,
            start_time=start_time,
            end_time=end_time,
            squareoff_time=squareoff_time
        )
        
        if strategy:
            # Schedule squareoff if intraday
            if is_intraday and squareoff_time:
                schedule_squareoff(strategy.id, db)
            
            return RedirectResponse(url=chartink_router.url_path_for('view_strategy', strategy_id=strategy.id), status_code=302)
        else:
            logger.error('Error creating strategy')
            return templates.TemplateResponse('chartink/new_strategy.html', {"request": request, "error": 'Error creating strategy'})
    except Exception as e:
        logger.error(f'Error creating strategy: {str(e)}')
        return templates.TemplateResponse('chartink/new_strategy.html', {"request": request, "error": 'Error creating strategy'})

@chartink_router.get('/{strategy_id}')
async def view_strategy(strategy_id: int, request: Request, user_id: str = Depends(check_session_validity_fastapi), db: Session = Depends(get_db)):
    """View strategy details"""
    if not user_id:
        return RedirectResponse(url=request.url_for('auth.login'))
        
    strategy = get_strategy(db, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # Check if strategy belongs to user
    if strategy.user_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    symbol_mappings = get_symbol_mappings(db, strategy_id)
    return templates.TemplateResponse('chartink/view_strategy.html', {"request": request, "strategy": strategy, "symbol_mappings": symbol_mappings})

@chartink_router.post('/{strategy_id}/delete')
async def delete_strategy_route(strategy_id: int, user_id: str = Depends(check_session_validity_fastapi), db: Session = Depends(get_db)):
    """Delete a strategy"""
    if not user_id:
        return JSONResponse(status_code=401, content={'status': 'error', 'error': 'Session expired'})
        
    strategy = get_strategy(db, strategy_id)
    if not strategy:
        return JSONResponse(status_code=404, content={'status': 'error', 'error': 'Strategy not found'})
    
    # Check if strategy belongs to user
    if strategy.user_id != user_id:
        return JSONResponse(status_code=403, content={'status': 'error', 'error': 'Unauthorized'})
    
    try:
        # Remove squareoff job if exists
        job_id = f'squareoff_{strategy_id}'
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
        
        # Delete strategy and its mappings
        if delete_strategy(db, strategy_id):
            return JSONResponse(status_code=200, content={'status': 'success'})
        else:
            return JSONResponse(status_code=500, content={'status': 'error', 'error': 'Failed to delete strategy'})
    except Exception as e:
        logger.error(f'Error deleting strategy {strategy_id}: {str(e)}')
        return JSONResponse(status_code=500, content={'status': 'error', 'error': str(e)})

@chartink_router.get('/{strategy_id}/configure')
async def configure_symbols_get(strategy_id: int, request: Request, user_id: str = Depends(check_session_validity_fastapi), db: Session = Depends(get_db)):
    """Configure symbols for strategy"""
    if not user_id:
        return RedirectResponse(url=request.url_for('auth.login'))
        
    strategy = get_strategy(db, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # Check if strategy belongs to user
    if strategy.user_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    symbol_mappings = get_symbol_mappings(db, strategy_id)
    return templates.TemplateResponse('chartink/configure_symbols.html', 
                                 {"request": request, 
                                  "strategy": strategy, 
                                  "symbol_mappings": symbol_mappings,
                                  "exchanges": VALID_EXCHANGES})

@chartink_router.post('/{strategy_id}/configure')
async def configure_symbols_post(
    strategy_id: int,
    request: Request,
    user_id: str = Depends(check_session_validity_fastapi),
    db: Session = Depends(get_db),
    # For form data, if not JSON
    symbol: str = Form(None),
    exchange: str = Form(None),
    quantity: str = Form(None),
    product_type: str = Form(None),
    symbols: str = Form(None) # For bulk upload
):
    """Configure symbols for strategy"""
    if not user_id:
        return JSONResponse(status_code=401, content={'status': 'error', 'error': 'Session expired'})
        
    strategy = get_strategy(db, strategy_id)
    if not strategy:
        return JSONResponse(status_code=404, content={'status': 'error', 'error': 'Strategy not found'})
    
    # Check if strategy belongs to user
    if strategy.user_id != user_id:
        return JSONResponse(status_code=403, content={'status': 'error', 'error': 'Unauthorized'})
    
    try:
        data = await request.json() if request.headers.get('content-type') == 'application/json' else {
            "symbol": symbol, "exchange": exchange, "quantity": quantity, "product_type": product_type, "symbols": symbols
        }
        
        logger.info(f"Received data: {data}")
        
        # Handle bulk symbols
        if 'symbols' in data and data['symbols'] is not None:
            symbols_text = data.get('symbols')
            mappings = []
            
            for line in symbols_text.strip().split('\n'):
                if not line.strip():
                    continue
                
                parts = line.strip().split(',')
                if len(parts) != 4:
                    raise ValueError(f'Invalid format in line: {line}')
                
                symbol_bulk, exchange_bulk, quantity_bulk, product_bulk = parts
                if exchange_bulk not in VALID_EXCHANGES:
                    raise ValueError(f'Invalid exchange: {exchange_bulk}')
                
                mappings.append({
                    'chartink_symbol': symbol_bulk.strip(),
                    'exchange': exchange_bulk.strip(),
                    'quantity': int(quantity_bulk),
                    'product_type': product_bulk.strip()
                })
            
            if mappings:
                bulk_add_symbol_mappings(db, strategy_id, mappings)
                return JSONResponse(status_code=200, content={'status': 'success'})
        
        # Handle single symbol
        else:
            symbol_single = data.get('symbol')
            exchange_single = data.get('exchange')
            quantity_single = data.get('quantity')
            product_type_single = data.get('product_type')
            
            logger.info(f"Processing single symbol: symbol={symbol_single}, exchange={exchange_single}, quantity={quantity_single}, product_type={product_type_single}")
            
            if not all([symbol_single, exchange_single, quantity_single, product_type_single]):
                missing = []
                if not symbol_single: missing.append('symbol')
                if not exchange_single: missing.append('exchange')
                if not quantity_single: missing.append('quantity')
                if not product_type_single: missing.append('product_type')
                raise ValueError(f'Missing required fields: {", ".join(missing)}')
            
            if exchange_single not in VALID_EXCHANGES:
                raise ValueError(f'Invalid exchange: {exchange_single}')
            
            try:
                quantity_single = int(quantity_single)
            except ValueError:
                raise ValueError('Quantity must be a valid number')
            
            if quantity_single <= 0:
                raise ValueError('Quantity must be greater than 0')
            
            mapping = add_symbol_mapping(
                db=db,
                strategy_id=strategy_id,
                chartink_symbol=symbol_single,
                exchange=exchange_single,
                quantity=quantity_single,
                product_type=product_type_single
            )
            
            if mapping:
                return JSONResponse(status_code=200, content={'status': 'success'})
            else:
                raise ValueError('Failed to add symbol mapping')
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error configuring symbols: {error_msg}')
        return JSONResponse(status_code=400, content={'status': 'error', 'error': error_msg})

@chartink_router.post('/{strategy_id}/symbol/{mapping_id}/delete')
async def delete_symbol(strategy_id: int, mapping_id: int, user_id: str = Depends(check_session_validity_fastapi), db: Session = Depends(get_db)):
    """Delete symbol mapping"""
    if not user_id:
        return JSONResponse(status_code=401, content={'status': 'error', 'error': 'Session expired'})
        
    strategy = get_strategy(db, strategy_id)
    if not strategy or strategy.user_id != user_id:
        return JSONResponse(status_code=404, content={'status': 'error', 'error': 'Strategy not found'})
    
    try:
        delete_symbol_mapping(db, mapping_id)
        return JSONResponse(status_code=200, content={'status': 'success'})
    except Exception as e:
        logger.error(f'Error deleting symbol mapping: {str(e)}')
        return JSONResponse(status_code=400, content={'status': 'error', 'error': str(e)})

@chartink_router.post('/{strategy_id}/toggle')
async def toggle_strategy_route(strategy_id: int, request: Request, user_id: str = Depends(check_session_validity_fastapi), db: Session = Depends(get_db)):
    """Toggle strategy active status"""
    if not user_id:
        return RedirectResponse(url=request.url_for('auth.login'))
        
    strategy = get_strategy(db, strategy_id)
    if not strategy or strategy.user_id != user_id:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    try:
        strategy = toggle_strategy(db, strategy_id)
        if strategy:
            # Flash messages are not directly supported in FastAPI, will log and redirect
            status = 'activated' if strategy.is_active else 'deactivated'
            logger.info(f'Strategy {status} successfully')
        else:
            logger.error('Error toggling strategy')
    except Exception as e:
        logger.error(f'Error toggling strategy: {str(e)}')
    
    return RedirectResponse(url=chartink_router.url_path_for('view_strategy', strategy_id=strategy_id), status_code=302)

@chartink_router.get('/search')
async def search_symbols(query: str, exchange: str = None, user_id: str = Depends(check_session_validity_fastapi), db: Session = Depends(get_db)):
    """Search symbols endpoint"""
    if not query:
        return JSONResponse(status_code=200, content={'results': []})
    
    results = enhanced_search_symbols(db, query, exchange)
    return JSONResponse(status_code=200, content={
        'results': [{
            'symbol': result.symbol,
            'name': result.name,
            'exchange': result.exchange
        } for result in results]
    })

@chartink_router.post('/webhook/{webhook_id}')
async def webhook(webhook_id: str, request: Request, db: Session = Depends(get_db)):
    """Handle webhook from Chartink"""
    try:
        # Get strategy by webhook ID
        strategy = get_strategy_by_webhook_id(db, webhook_id)
        if not strategy:
            logger.error(f'Strategy not found for webhook ID: {webhook_id}')
            return JSONResponse(status_code=404, content={'status': 'error', 'error': 'Invalid webhook ID'})
        
        if not strategy.is_active:
            logger.info(f'Strategy {strategy.id} is inactive, ignoring webhook')
            return JSONResponse(status_code=200, content={'status': 'success', 'message': 'Strategy is inactive'})
        
        # Parse webhook data
        data = await request.json()
        if not data:
            logger.error(f'No data received in webhook for strategy {strategy.id}')
            return JSONResponse(status_code=400, content={'status': 'error', 'error': 'No data received'})
        
        logger.info(f'Received webhook data: {data}')
        
        # Determine action from scan name first to apply correct time checks
        scan_name = data.get('scan_name', '').upper()
        if 'BUY' in scan_name:
            action = 'BUY'
            use_smart_order = False
            is_entry_order = True
        elif 'SELL' in scan_name:
            action = 'SELL'
            use_smart_order = True
            is_entry_order = False
        elif 'SHORT' in scan_name:
            action = 'SELL'  # For short entry
            use_smart_order = False
            is_entry_order = True
        elif 'COVER' in scan_name:
            action = 'BUY'   # For short cover
            use_smart_order = True
            is_entry_order = False
        else:
            error_msg = 'No valid action keyword (BUY/SELL/SHORT/COVER) found in scan name'
            logger.error(error_msg)
            return JSONResponse(status_code=400, content={'status': 'error', 'error': error_msg})
            
        # Time validations for intraday strategies
        if strategy.is_intraday:
            current_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
            
            # Convert strategy times to time objects
            start_time = datetime.strptime(strategy.start_time, '%H:%M').time()
            end_time = datetime.strptime(strategy.end_time, '%H:%M').time()
            squareoff_time = datetime.strptime(strategy.squareoff_time, '%H:%M').time()
            
            # Check if before start time for all orders
            if current_time < start_time:
                logger.info(f'Strategy {strategy.id} received webhook before start time, ignoring')
                return JSONResponse(status_code=400, content={
                    'status': 'error',
                    'error': 'Cannot place orders before start time'
                })
            
            # Check if after squareoff time for all orders
            if current_time >= squareoff_time:
                logger.info(f'Strategy {strategy.id} received webhook after squareoff time, ignoring')
                return JSONResponse(status_code=400, content={
                    'status': 'error',
                    'error': 'Cannot place orders after squareoff time'
                })
            
            # For entry orders (BUY/SHORT), check end time
            if is_entry_order and current_time >= end_time:
                logger.info(f'Strategy {strategy.id} received entry order after end time, ignoring')
                return JSONResponse(status_code=400, content={
                    'status': 'error',
                    'error': 'Cannot place entry orders after end time'
                })
        
        # Get symbols and trigger prices
        symbols = data.get('stocks', '').split(',')
        # trigger_prices = data.get('trigger_prices', '').split(',') # Not used in Flask version
        
        if not symbols:
            logger.error('No symbols received in webhook')
            return JSONResponse(status_code=400, content={'status': 'error', 'error': 'No symbols received'})
        
        # Get symbol mappings
        mappings = get_symbol_mappings(db, strategy.id)
        if not mappings:
            logger.error(f'No symbol mappings found for strategy {strategy.id}')
            return JSONResponse(status_code=400, content={'status': 'error', 'error': 'No symbol mappings configured'})
        
        mapping_dict = {m.chartink_symbol: m for m in mappings}
        
        # Get API key from database
        api_key = get_api_key_for_tradingview(db, strategy.user_id)
        if not api_key:
            logger.error(f'No API key found for user {strategy.user_id}')
            return JSONResponse(status_code=401, content={'status': 'error', 'error': 'No API key found'})
        
        # Process each symbol
        processed_symbols = []
        for symbol in symbols:
            symbol = symbol.strip()
            if not symbol:
                continue
                
            mapping = mapping_dict.get(symbol)
            if not mapping:
                logger.warning(f'No mapping found for symbol {symbol} in strategy {strategy.id}')
                continue
            
            # Prepare base payload
            payload = {
                'apikey': api_key,
                'strategy': strategy.name,
                'symbol': mapping.chartink_symbol,
                'exchange': mapping.exchange,
                'action': action,
                'product': mapping.product_type,
                'pricetype': 'MARKET'
            }
            
            # Add quantity based on order type
            if use_smart_order:
                # For SELL and COVER, use smart order with quantity=0 and position_size=0
                payload.update({
                    'quantity': '0',
                    'position_size': '0',
                    'price': '0',
                    'trigger_price': '0',
                    'disclosed_quantity': '0'
                })
                endpoint = 'placesmartorder'
            else:
                # For BUY and SHORT, use regular order with configured quantity
                payload.update({
                    'quantity': str(mapping.quantity)
                })
                endpoint = 'placeorder'
            
            logger.info(f'Queueing {endpoint} with payload: {payload}')
            
            # Queue the order instead of executing directly
            queue_order(endpoint, payload)
            processed_symbols.append(symbol)
        
        if processed_symbols:
            return JSONResponse(status_code=200, content={
                'status': 'success',
                'message': f'Orders queued for symbols: {", ".join(processed_symbols)}'
            })
        else:
            return JSONResponse(status_code=200, content={
                'status': 'warning',
                'message': 'No orders were queued'
            })
        
    except Exception as e:
        logger.error(f'Error processing webhook: {str(e)}')
        return JSONResponse(status_code=500, content={'status': 'error', 'error': str(e)})
