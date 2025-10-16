from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from collections import defaultdict
import numpy as np
from datetime import datetime
import pytz
import csv
import io

from app.db.session import get_db
from app.utils.session import check_session_validity_fastapi
from app.db.latency_db import OrderLatency # Assuming OrderLatency is still valid
from app.core.config import settings # Assuming settings for templates directory
from app.utils.web import limiter # Assuming limiter is in this path
from app.core.config import settings # Assuming settings for templates directory
from app.utils.logging import logger
from app.web.frontend import templates


latency_router = APIRouter(prefix="/latency", tags=["Latency"])

#TODO: move to utils
def convert_to_ist(timestamp):
    """Convert UTC timestamp to IST"""
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    utc = pytz.timezone('UTC')
    ist = pytz.timezone('Asia/Kolkata')
    if timestamp.tzinfo is None:
        timestamp = utc.localize(timestamp)
    return timestamp.astimezone(ist)

#TODO: move to utils
def format_ist_time(timestamp):
    """Format timestamp in IST with 12-hour format"""
    ist_time = convert_to_ist(timestamp)
    return ist_time.strftime('%d-%m-%Y %I:%M:%S %p')

#TODO: move to latency_db file
def get_histogram_data(db: Session, broker: str = None):
    """Get histogram data for RTT distribution"""
    try:
        query = db.query(OrderLatency.rtt_ms)
        if broker:
            query = query.filter(OrderLatency.broker == broker)
        
        # Get all RTT values
        rtts = [r[0] for r in query.all()]
        
        if not rtts:
            return {
                'bins': [],
                'counts': [],
                'avg_rtt': 0,
                'min_rtt': 0,
                'max_rtt': 0
            }
        
        # Calculate statistics
        avg_rtt = sum(rtts) / len(rtts)
        min_rtt = min(rtts)
        max_rtt = max(rtts)
        
        # Create histogram bins
        bin_count = 30  # Number of bins
        bin_width = (max_rtt - min_rtt) / bin_count if max_rtt > min_rtt else 1
        
        # Create histogram using numpy
        counts, bins = np.histogram(rtts, bins=bin_count, range=(min_rtt, max_rtt))
        
        # Convert to list for JSON serialization
        counts = counts.tolist()
        bins = bins.tolist()
        
        # Create bin labels (use the start of each bin)
        bin_labels = [f"{bins[i]:.1f}" for i in range(len(bins)-1)]
        
        data = {
            'bins': bin_labels,
            'counts': counts,
            'avg_rtt': float(avg_rtt),
            'min_rtt': float(min_rtt),
            'max_rtt': float(max_rtt)
        }
        
        return data
        
    except Exception as e:
        logger.error(f"Error getting histogram data: {e}")
        return {
            'bins': [],
            'counts': [],
            'avg_rtt': 0,
            'min_rtt': 0,
            'max_rtt': 0
        }

def generate_csv(logs):
    """Generate CSV file from latency logs"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Timestamp', 'Broker', 'Order ID', 'Symbol', 'Order Type', 'RTT (ms)', 'Overhead (ms)', 'Total Latency (ms)', 'Status'])
    
    # Write data
    for log in logs:
        writer.writerow([
            format_ist_time(log.timestamp),
            log.broker,
            log.order_id,
            log.symbol,
            log.order_type,
            round(log.rtt_ms, 2),
            round(log.overhead_ms, 2),
            round(log.total_latency_ms, 2),
            log.status
        ])
    
    return output.getvalue()

@latency_router.get("/", dependencies=[Depends(check_session_validity_fastapi)])
@limiter.limit("60/minute")
async def latency_dashboard(request: Request, db: Session = Depends(get_db)):
    """Display latency monitoring dashboard"""
    stats = OrderLatency.get_latency_stats(db)
    recent_logs = OrderLatency.get_recent_logs(db, limit=100)
    
    # Get histogram data for each broker
    broker_histograms = {}
    brokers = [b[0] for b in db.query(OrderLatency.broker).distinct().all()]
    for broker in brokers:
        if broker:  # Skip None values
            broker_histograms[broker] = get_histogram_data(db, broker)
    
    # Format timestamps in IST
    for log in recent_logs:
        log.formatted_timestamp = format_ist_time(log.timestamp)
    
    return templates.TemplateResponse('latency/dashboard.html',
                                  {"request": request,
                                   "stats": stats,
                                   "logs": recent_logs,
                                   "broker_histograms": broker_histograms})

@latency_router.get("/api/logs", dependencies=[Depends(check_session_validity_fastapi)])
@limiter.limit("60/minute")
async def get_logs(request: Request, db: Session = Depends(get_db), limit: int = 100):
    """API endpoint to get latency logs"""
    try:
        limit = min(limit, 1000)
        logs = OrderLatency.get_recent_logs(db, limit=limit)
        return JSONResponse([{
            'timestamp': convert_to_ist(log.timestamp).isoformat(),
            'id': log.id,
            'order_id': log.order_id,
            'broker': log.broker,
            'symbol': log.symbol,
            'order_type': log.order_type,
            'rtt_ms': log.rtt_ms,
            'validation_latency_ms': log.validation_latency_ms,
            'response_latency_ms': log.response_latency_ms,
            'overhead_ms': log.overhead_ms,
            'total_latency_ms': log.total_latency_ms,
            'status': log.status,
            'error': log.error
        } for log in logs])
    except Exception as e:
        logger.error(f"Error fetching latency logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@latency_router.get("/api/stats", dependencies=[Depends(check_session_validity_fastapi)])
@limiter.limit("60/minute")
async def get_stats(request: Request, db: Session = Depends(get_db)):
    """API endpoint to get latency statistics"""
    try:
        stats = OrderLatency.get_latency_stats(db)
        
        # Add histogram data for each broker
        broker_histograms = {}
        for broker in stats.get('broker_stats', {}):
            broker_histograms[broker] = get_histogram_data(db, broker)
        
        stats['broker_histograms'] = broker_histograms
        return JSONResponse(stats)
    except Exception as e:
        logger.error(f"Error fetching latency stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@latency_router.get("/api/broker/{broker}/stats", dependencies=[Depends(check_session_validity_fastapi)])
@limiter.limit("60/minute")
async def get_broker_stats(request: Request, broker: str, db: Session = Depends(get_db)):
    """API endpoint to get broker-specific latency statistics"""
    try:
        stats = OrderLatency.get_latency_stats(db)
        broker_stats = stats.get('broker_stats', {}).get(broker, {})
        if not broker_stats:
            raise HTTPException(status_code=404, detail="Broker not found")
        
        # Add histogram data
        broker_stats['histogram'] = get_histogram_data(db, broker)
        return JSONResponse(broker_stats)
    except Exception as e:
        logger.error(f"Error fetching broker stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@latency_router.get("/export", dependencies=[Depends(check_session_validity_fastapi)])
@limiter.limit("10/minute")
async def export_logs(request: Request, db: Session = Depends(get_db)):
    """Export latency logs to CSV"""
    try:
        # Get all logs for the current day
        logs = OrderLatency.get_recent_logs(db, limit=None)  # None to get all logs
        
        # Generate CSV
        csv_data = generate_csv(logs)
        
        return StreamingResponse(
            io.BytesIO(csv_data.encode('utf-8')),
            media_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename=latency_logs.csv'}
        )
        
    except Exception as e:
        logger.error(f"Error exporting latency logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))