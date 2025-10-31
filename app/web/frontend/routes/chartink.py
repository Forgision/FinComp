import queue
import threading
import time as time_module
import uuid
from collections import deque
from time import time

import pytz
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.templating import Jinja2Templates

from app.core.config import settings
from app.core.services.limiter_service import limiter
from app.core.models.auth_db import get_api_key_for_tradingview
from app.core.models.chartink_db import (
    create_strategy,
    delete_strategy,
    get_strategy,
    get_strategy_by_webhook_id,
    get_symbol_mappings,
    get_user_strategies,
)
from app.utils.logging import logger
from app.utils.session import check_session_validity_fastapi

templates = Jinja2Templates(directory="app/frontend/templates")

WEBHOOK_RATE_LIMIT = settings.WEBHOOK_RATE_LIMIT
STRATEGY_RATE_LIMIT = settings.STRATEGY_RATE_LIMIT

chartink_router = APIRouter(prefix="/chartink")

scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Kolkata"))

# In-memory queues and state (WARNING: Not suitable for multi-worker production)
regular_order_queue = queue.Queue()
smart_order_queue = queue.Queue()
order_processor_running = False
order_processor_lock = threading.Lock()
last_regular_orders = deque(maxlen=10)

def process_orders_sync():
    """Synchronous order processing function to be run in a separate thread."""
    while True:
        try:
            # Process smart orders
            try:
                smart_order = smart_order_queue.get_nowait()
                if smart_order is None:
                    break
                requests.post(f"{settings.HOST_SERVER}/api/v1/placesmartorder", json=smart_order['payload'])
                time_module.sleep(1)
                continue
            except queue.Empty:
                pass

            # Process regular orders
            now = time()
            while last_regular_orders and now - last_regular_orders[0] > 1:
                last_regular_orders.popleft()

            if len(last_regular_orders) < 10:
                try:
                    regular_order = regular_order_queue.get_nowait()
                    if regular_order is None:
                        break
                    requests.post(f"{settings.HOST_SERVER}/api/v1/placeorder", json=regular_order['payload'])
                    last_regular_orders.append(now)
                except queue.Empty:
                    time_module.sleep(0.1)
            else:
                time_module.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in order processor: {e}")
            time_module.sleep(0.1)

def ensure_order_processor():
    global order_processor_running
    with order_processor_lock:
        if not order_processor_running:
            order_processor_running = True
            thread = threading.Thread(target=process_orders_sync, daemon=True)
            thread.start()

def queue_order(endpoint, payload):
    ensure_order_processor()
    if endpoint == 'placesmartorder':
        smart_order_queue.put({'endpoint': endpoint, 'payload': payload})
    else:
        regular_order_queue.put({'endpoint': endpoint, 'payload': payload})

async def squareoff_positions(strategy_id: int):
    # This needs to be async to be scheduled with AsyncIOScheduler
    # ... implementation would be similar to original but using async httpx client
    logger.info(f"Squaring off positions for strategy {strategy_id}")


@chartink_router.on_event("startup")
async def startup_event():
    scheduler.start()
    ensure_order_processor()
    # Reschedule jobs from DB if necessary
    logger.info("Chartink router started, scheduler and order processor running.")

@chartink_router.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    regular_order_queue.put(None)
    smart_order_queue.put(None)
    logger.info("Chartink router stopped.")


@chartink_router.get("/", dependencies=[Depends(check_session_validity_fastapi)])
async def index(request: Request):
    user_id = request.session.get("user")
    strategies = get_user_strategies(user_id)
    return templates.TemplateResponse("chartink/index.html", {"request": request, "strategies": strategies})

@chartink_router.get("/new", dependencies=[Depends(check_session_validity_fastapi)])
async def new_strategy_form(request: Request):
    return templates.TemplateResponse("chartink/new_strategy.html", {"request": request})

@chartink_router.post("/new", dependencies=[Depends(check_session_validity_fastapi)])
@limiter.limit(STRATEGY_RATE_LIMIT)
async def create_strategy_post(request: Request):
    user_id = request.session.get("user")
    form_data = await request.form()
    name = form_data.get("name", "").strip()
    # ... (rest of the logic from original new_strategy)
    webhook_id = str(uuid.uuid4())
    new_strategy = create_strategy(name=f"chartink_{name}", webhook_id=webhook_id, user_id=user_id)
    return RedirectResponse(url=f"/chartink/{new_strategy.id}", status_code=303)


@chartink_router.get("/{strategy_id}", dependencies=[Depends(check_session_validity_fastapi)])
async def view_strategy(request: Request, strategy_id: int):
    user_id = request.session.get("user")
    strategy = get_strategy(strategy_id)
    if not strategy or strategy.user_id != user_id:
        raise HTTPException(status_code=404, detail="Strategy not found")
    symbol_mappings = get_symbol_mappings(strategy_id)
    return templates.TemplateResponse("chartink/view_strategy.html", {
        "request": request,
        "strategy": strategy,
        "symbol_mappings": symbol_mappings
    })

@chartink_router.post("/{strategy_id}/delete", dependencies=[Depends(check_session_validity_fastapi)])
@limiter.limit(STRATEGY_RATE_LIMIT)
async def delete_strategy_route(request: Request, strategy_id: int):
    user_id = request.session.get("user")
    strategy = get_strategy(strategy_id)
    if not strategy or strategy.user_id != user_id:
        return JSONResponse({"status": "error", "error": "Unauthorized"}, status_code=403)
    
    job_id = f'squareoff_{strategy_id}'
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    
    if delete_strategy(strategy_id):
        return JSONResponse({"status": "success"})
    else:
        return JSONResponse({"status": "error", "error": "Failed to delete strategy"}, status_code=500)


@chartink_router.post("/webhook/{webhook_id}")
@limiter.limit(WEBHOOK_RATE_LIMIT)
async def webhook(webhook_id: str, request: Request):
    strategy = get_strategy_by_webhook_id(webhook_id)
    if not strategy or not strategy.is_active:
        return JSONResponse({"status": "success", "message": "Strategy inactive or not found"})

    data = await request.json()
    scan_name = data.get("scan_name", "").upper()
    
    if "BUY" in scan_name:
        action, use_smart_order = "BUY", False
    elif "SELL" in scan_name:
        action, use_smart_order = "SELL", True
    elif "SHORT" in scan_name:
        action, use_smart_order = "SELL", False
    elif "COVER" in scan_name:
        action, use_smart_order = "BUY", True
    else:
        return JSONResponse({"status": "error", "error": "Invalid action in scan name"}, status_code=400)

    # Time validation logic would go here...

    symbols = data.get("stocks", "").split(",")
    mappings = get_symbol_mappings(strategy.id)
    mapping_dict = {m.chartink_symbol: m for m in mappings}
    api_key = get_api_key_for_tradingview(strategy.user_id)

    if not api_key:
        return JSONResponse({"status": "error", "error": "API key not found"}, status_code=401)

    processed_symbols = []
    for symbol in symbols:
        if not (mapping := mapping_dict.get(symbol.strip())):
            continue

        payload = {
            "apikey": api_key, "strategy": strategy.name, "symbol": mapping.chartink_symbol,
            "exchange": mapping.exchange, "action": action, "product": mapping.product_type,
            "pricetype": "MARKET"
        }
        
        if use_smart_order:
            payload.update({"quantity": "0", "position_size": "0"})
            endpoint = "placesmartorder"
        else:
            payload.update({"quantity": str(mapping.quantity)})
            endpoint = "placeorder"
        
        queue_order(endpoint, payload)
        processed_symbols.append(symbol)

    if processed_symbols:
        return JSONResponse({"status": "success", "message": f"Orders queued for: {', '.join(processed_symbols)}"})
    else:
        return JSONResponse({"status": "warning", "message": "No orders were queued"})

# ... other routes to be refactored