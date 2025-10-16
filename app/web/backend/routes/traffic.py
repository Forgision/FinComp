import logging
from datetime import datetime
import pytz
import csv
import io
from fastapi import APIRouter, Depends, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import func
from app.db.traffic_db import TrafficLog, logs_session
from .security import get_logs_db
from app.utils.session import check_session_validity_fastapi
from app.utils.logging import logger
from app.utils.web import limiter
from app.web.frontend import templates

traffic_router = APIRouter(prefix="/traffic", tags=["Traffic Monitoring"])

def convert_to_ist(timestamp):
    """Convert UTC timestamp to IST"""
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    utc = pytz.timezone('UTC')
    ist = pytz.timezone('Asia/Kolkata')
    if timestamp.tzinfo is None:
        timestamp = utc.localize(timestamp)
    return ist.localize(timestamp).astimezone(ist)

def format_ist_time(timestamp):
    """Format timestamp in IST with 12-hour format"""
    ist_time = convert_to_ist(timestamp)
    return ist_time.strftime('%d-%m-%Y %I:%M:%S %p')

def generate_csv(logs):
    """Generate CSV file from traffic logs"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Timestamp', 'Client IP', 'Method', 'Path', 'Status Code', 'Duration (ms)', 'Host', 'Error'])
    
    # Write data
    for log in logs:
        writer.writerow([
            format_ist_time(log.timestamp),
            log.client_ip,
            log.method,
            log.path,
            log.status_code,
            round(log.duration_ms, 2),
            log.host,
            log.error
        ])
    
    return output.getvalue()

@traffic_router.get("/", response_class=HTMLResponse)
@limiter.limit("60/minute")
async def traffic_dashboard(request: Request, db: Session = Depends(get_logs_db), session_data: dict = Depends(check_session_validity_fastapi)):
    """Display traffic monitoring dashboard"""
    stats = TrafficLog.get_stats()
    recent_logs = TrafficLog.get_recent_logs(limit=100)
    # Convert TrafficLog objects to dictionaries with IST timestamps
    logs_data = [{
        'timestamp': format_ist_time(log.timestamp),
        'client_ip': log.client_ip,
        'method': log.method,
        'path': log.path,
        'status_code': log.status_code,
        'duration_ms': round(log.duration_ms, 2),
        'host': log.host,
        'error': log.error
    } for log in recent_logs]
    return templates.TemplateResponse("traffic/dashboard.html", {
        "request": request,
        "stats": stats,
        "logs": logs_data,
        "session": session_data
    })

@traffic_router.get("/api/logs", response_class=JSONResponse)
@limiter.limit("60/minute")
async def get_logs(request: Request, db: Session = Depends(get_logs_db), session_data: dict = Depends(check_session_validity_fastapi)):
    """API endpoint to get traffic logs"""
    try:
        limit = int(request.query_params.get('limit', 100))
        limit = min(limit, 1000)
        logs = TrafficLog.get_recent_logs(limit=limit)
        return JSONResponse(content=[{
            'timestamp': format_ist_time(log.timestamp),
            'client_ip': log.client_ip,
            'method': log.method,
            'path': log.path,
            'status_code': log.status_code,
            'duration_ms': round(log.duration_ms, 2),
            'host': log.host,
            'error': log.error
        } for log in logs])
    except Exception as e:
        logger.error(f"Error fetching traffic logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@traffic_router.get("/api/stats", response_class=JSONResponse)
@limiter.limit("60/minute")
async def get_stats(request: Request, db: Session = Depends(get_logs_db), session_data: dict = Depends(check_session_validity_fastapi)):
    """API endpoint to get traffic statistics"""
    try:
        # Get overall stats
        all_logs = db.query(TrafficLog)
        overall_stats = {
            'total_requests': all_logs.count(),
            'error_requests': all_logs.filter(TrafficLog.status_code >= 400).count(),
            'avg_duration': round(float(all_logs.with_entities(func.avg(TrafficLog.duration_ms)).scalar() or 0), 2)
        }
        
        # Get API-specific stats
        api_logs = db.query(TrafficLog).filter(TrafficLog.path.like('/api/v1/%'))
        api_stats = {
            'total_requests': api_logs.count(),
            'error_requests': api_logs.filter(TrafficLog.status_code >= 400).count(),
            'avg_duration': round(float(api_logs.with_entities(func.avg(TrafficLog.duration_ms)).scalar() or 0), 2)
        }
        
        # Get endpoint usage stats
        endpoint_stats = {}
        for endpoint in [
            'placeorder', 'placesmartorder', 'modifyorder', 'cancelorder',
            'quotes', 'history', 'depth', 'intervals', 'funds', 'orderbook',
            'tradebook', 'positionbook', 'holdings', 'basketorder', 'splitorder',
            'orderstatus', 'openposition'
        ]:
            path = f'/api/v1/{endpoint}'
            endpoint_logs = db.query(TrafficLog).filter(TrafficLog.path.like(f'{path}%'))
            endpoint_stats[endpoint] = {
                'total': endpoint_logs.count(),
                'errors': endpoint_logs.filter(TrafficLog.status_code >= 400).count(),
                'avg_duration': round(float(endpoint_logs.with_entities(func.avg(TrafficLog.duration_ms)).scalar() or 0), 2)
            }
        
        return JSONResponse(content={
            'overall': overall_stats,
            'api': api_stats,
            'endpoints': endpoint_stats
        })
    except Exception as e:
        logger.error(f"Error fetching traffic stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@traffic_router.get("/export", response_class=Response)
@limiter.limit("10/minute")
async def export_logs(request: Request, db: Session = Depends(get_logs_db), session_data: dict = Depends(check_session_validity_fastapi)):
    """Export traffic logs to CSV"""
    try:
        # Get all logs for the current day
        logs = TrafficLog.get_recent_logs(limit=None)  # None to get all logs
        
        # Generate CSV
        csv_data = generate_csv(logs)
        
        # Create the response
        return Response(
            content=csv_data,
            media_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename=traffic_logs.csv'}
        )
        
    except Exception as e:
        logger.error(f"Error exporting traffic logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
