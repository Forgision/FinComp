from datetime import datetime

import numpy as np
import pytz
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from app.core.services.limiter_service import limiter
from app.db.schemas.latency_db import OrderLatency, latency_session
from app.utils.logging import get_logger
from app.utils.session import check_session_validity_fastapi

logger = get_logger(__name__)
templates = Jinja2Templates(directory="app/frontend/templates")

latency_router = APIRouter(prefix="/latency")

def get_latency_db():
    db = latency_session()
    try:
        yield db
    finally:
        db.close()

def convert_to_ist(timestamp):
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    utc = pytz.timezone('UTC')
    ist = pytz.timezone('Asia/Kolkata')
    if timestamp.tzinfo is None:
        timestamp = utc.localize(timestamp)
    return timestamp.astimezone(ist)

def format_ist_time(timestamp):
    ist_time = convert_to_ist(timestamp)
    return ist_time.strftime('%d-%m-%Y %I:%M:%S %p')

def get_histogram_data(db: Session, broker=None):
    try:
        query = db.query(OrderLatency)
        if broker:
            query = query.filter(OrderLatency.broker == broker)
        
        rtts = [r.rtt_ms for r in query.all()]
        if not rtts:
            return {'bins': [], 'counts': [], 'avg_rtt': 0, 'min_rtt': 0, 'max_rtt': 0}

        avg_rtt = sum(rtts) / len(rtts)
        min_rtt = min(rtts)
        max_rtt = max(rtts)
        
        counts, bins = np.histogram(rtts, bins=30, range=(min_rtt, max_rtt))
        bin_labels = [f"{bins[i]:.1f}" for i in range(len(bins)-1)]
        
        return {
            'bins': bin_labels, 'counts': counts.tolist(), 'avg_rtt': float(avg_rtt),
            'min_rtt': float(min_rtt), 'max_rtt': float(max_rtt)
        }
    except Exception as e:
        logger.error(f"Error getting histogram data: {e}")
        return {'bins': [], 'counts': [], 'avg_rtt': 0, 'min_rtt': 0, 'max_rtt': 0}

@latency_router.get("/", dependencies=[Depends(check_session_validity_fastapi)])
@limiter.limit("60/minute")
async def latency_dashboard(request: Request, db: Session = Depends(get_latency_db)):
    stats = OrderLatency.get_latency_stats(db)
    recent_logs = OrderLatency.get_recent_logs(db, limit=100)
    
    broker_histograms = {}
    brokers = [b[0] for b in db.query(OrderLatency.broker).distinct().all()]
    for broker in brokers:
        if broker:
            broker_histograms[broker] = get_histogram_data(db, broker)
            
    for log in recent_logs:
        log.formatted_timestamp = format_ist_time(log.timestamp)
        
    return templates.TemplateResponse(
        "latency/dashboard.html",
        {"request": request, "stats": stats, "logs": recent_logs, "broker_histograms": broker_histograms}
    )

@latency_router.get("/api/logs", dependencies=[Depends(check_session_validity_fastapi)])
@limiter.limit("60/minute")
async def get_logs(request: Request, limit: int = 100, db: Session = Depends(get_latency_db)):
    try:
        logs = OrderLatency.get_recent_logs(db, limit=min(limit, 1000))
        return JSONResponse([log.to_dict() for log in logs])
    except Exception as e:
        logger.error(f"Error fetching latency logs: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)

# ... other routes can be refactored similarly