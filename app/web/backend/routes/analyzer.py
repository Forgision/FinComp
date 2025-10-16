from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import pytz
import json
import io
import csv
import traceback
import os

from app.db.analyzer_db import AnalyzerLog
from app.db.session import get_db
from app.utils.api_analyzer import get_analyzer_stats
from app.utils.logging import logger
from app.utils.session import check_session_validity_fastapi
from app.web.frontend import templates

analyzer_router = APIRouter(prefix="/analyzer", tags=["analyzer"])

async def get_current_user(user: str = Depends(check_session_validity_fastapi)):
    return user


def format_request(req, ist):
    """Format a single request entry"""
    try:
        request_data = json.loads(req.request_data) if isinstance(req.request_data, str) else req.request_data
        response_data = json.loads(req.response_data) if isinstance(req.response_data, str) else req.response_data
        
        # Base request info
        formatted_request = {
            'timestamp': req.created_at.astimezone(ist).strftime('%Y-%m-%d %H:%M:%S'),
            'api_type': req.api_type,
            'source': request_data.get('strategy', 'Unknown'),
            'request_data': request_data,
            'response_data': response_data,  # Include complete response data
            'analysis': {
                'issues': response_data.get('status') == 'error',
                'error': response_data.get('message'),
                'error_type': 'error' if response_data.get('status') == 'error' else 'success',
                'warnings': response_data.get('warnings', [])
            }
        }

        # Add fields based on API type
        if req.api_type in ['placeorder', 'placesmartorder']:
            formatted_request.update({
                'symbol': request_data.get('symbol', 'Unknown'),
                'exchange': request_data.get('exchange', 'Unknown'),
                'action': request_data.get('action', 'Unknown'),
                'quantity': request_data.get('quantity', 0),
                'price_type': request_data.get('pricetype', 'Unknown'),
                'product_type': request_data.get('product', 'Unknown')
            })
            if req.api_type == 'placesmartorder':
                formatted_request['position_size'] = request_data.get('position_size', 0)
        elif req.api_type == 'cancelorder':
            formatted_request.update({
                'orderid': request_data.get('orderid', 'Unknown')
            })
        
        return formatted_request
    except Exception as e:
        logger.error(f"Error formatting request {req.id}: {str(e)}")
        return None

def get_recent_requests(db: Session):
    """Get recent analyzer requests"""
    try:
        ist = pytz.timezone('Asia/Kolkata')
        recent = db.query(AnalyzerLog).order_by(AnalyzerLog.created_at.desc()).limit(100).all()
        requests = []
        
        for req in recent:
            formatted = format_request(req, ist)
            if formatted:
                requests.append(formatted)
                
        return requests
    except Exception as e:
        logger.error(f"Error getting recent requests: {str(e)}")
        return []

def get_filtered_requests(db: Session, start_date: str = None, end_date: str = None):
    """Get analyzer requests with date filtering"""
    try:
        ist = pytz.timezone('Asia/Kolkata')
        query = db.query(AnalyzerLog)

        # Apply date filters if provided
        if start_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(AnalyzerLog.created_at >= start_date_obj)
        if end_date:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            # To include the entire end_date, filter up to the end of the day
            query = query.filter(AnalyzerLog.created_at < (end_date_obj + timedelta(days=1)))
        
        # If no dates provided, default to today
        if not start_date and not end_date:
            today_ist = datetime.now(ist).date()
            query = query.filter(AnalyzerLog.created_at >= today_ist)
            query = query.filter(AnalyzerLog.created_at < (today_ist + timedelta(days=1)))

        # Get results ordered by created_at
        results = query.order_by(AnalyzerLog.created_at.desc()).all()
        requests = []
        
        for req in results:
            formatted = format_request(req, ist)
            if formatted:
                requests.append(formatted)
                
        return requests
    except Exception as e:
        logger.error(f"Error getting filtered requests: {str(e)}\n{traceback.format_exc()}")
        return []

def generate_csv(requests):
    """Generate CSV from analyzer requests"""
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        headers = ['Timestamp', 'API Type', 'Source', 'Symbol', 'Exchange', 'Action', 
                  'Quantity', 'Price Type', 'Product Type', 'Status', 'Error Message']
        writer.writerow(headers)
        
        # Write data
        for req in requests:
            row = [
                req['timestamp'],
                req['api_type'],
                req['source'],
                req.get('symbol', ''),
                req.get('exchange', ''),
                req.get('action', ''),
                req.get('quantity', ''),
                req.get('price_type', ''),
                req.get('product_type', ''),
                'Error' if req['analysis']['issues'] else 'Success',
                req['analysis'].get('error', '')
            ]
            writer.writerow(row)
        
        return output.getvalue()
    except Exception as e:
        logger.error(f"Error generating CSV: {str(e)}\n{traceback.format_exc()}")
        return ""

@analyzer_router.get("/")
async def analyzer(
    request: Request,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    start_date: str = None,
    end_date: str = None
):
    """Render the analyzer dashboard"""
    try:
        # Get stats with proper structure
        stats = get_analyzer_stats()
        if not isinstance(stats, dict):
            stats = {
                'total_requests': 0,
                'sources': {},
                'symbols': [],
                'issues': {
                    'total': 0,
                    'by_type': {
                        'rate_limit': 0,
                        'invalid_symbol': 0,
                        'missing_quantity': 0,
                        'invalid_exchange': 0,
                        'other': 0
                    }
                }
            }

        # Get filtered requests
        requests = get_filtered_requests(db, start_date, end_date)
        
        return templates.TemplateResponse(
            "analyzer.html",
            {
                "request": request,
                "requests": requests,
                "stats": stats,
                "start_date": start_date,
                "end_date": end_date,
                "current_user": current_user, # Pass current_user to template
            }
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error rendering analyzer: {str(e)}\n{traceback.format_exc()}")
        # FastAPI doesn't have flash messages like Flask.
        # You might want to add a dependency for flash messages or handle errors differently.
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Error loading analyzer dashboard"},
            status_code=500
        )

@analyzer_router.get("/stats")
async def get_stats(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Get analyzer stats endpoint"""
    try:
        stats = get_analyzer_stats()
        return JSONResponse(stats)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error getting analyzer stats: {str(e)}")
        return JSONResponse({
            'total_requests': 0,
            'sources': {},
            'symbols': [],
            'issues': {
                'total': 0,
                'by_type': {
                    'rate_limit': 0,
                    'invalid_symbol': 0,
                    'missing_quantity': 0,
                    'invalid_exchange': 0,
                    'other': 0
                }
            }
        }, status_code=500)

@analyzer_router.get("/requests")
async def get_requests(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Get analyzer requests endpoint"""
    try:
        requests = get_recent_requests(db)
        return JSONResponse({'requests': requests})
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error getting analyzer requests: {str(e)}")
        return JSONResponse({'requests': []}, status_code=500)

@analyzer_router.get("/clear")
async def clear_logs(
    request: Request,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Clear analyzer logs"""
    try:
        # Delete all logs older than 24 hours
        cutoff = datetime.now(pytz.UTC) - timedelta(hours=24)
        db.query(AnalyzerLog).filter(AnalyzerLog.created_at < cutoff).delete()
        db.commit()
        # In FastAPI, you might use a redirect with a query parameter for a message, or a dedicated flash message system
        return Response(status_code=303, headers={"Location": "/analyzer?message=Logs cleared successfully"})
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error clearing analyzer logs: {str(e)}")
        return Response(status_code=303, headers={"Location": "/analyzer?error=Error clearing logs"})

@analyzer_router.get("/export")
async def export_requests(
    request: Request,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    start_date: str = None,
    end_date: str = None
):
    """Export analyzer requests to CSV"""
    try:
        # Get filtered requests
        requests = get_filtered_requests(db, start_date, end_date)
        
        # Generate CSV
        csv_data = generate_csv(requests)
        
        # Create the response
        response = Response(content=csv_data, media_type='text/csv')
        response.headers["Content-Disposition"] = f"attachment; filename=analyzer_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return response
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error exporting requests: {str(e)}\n{traceback.format_exc()}")
        return Response(status_code=303, headers={"Location": "/analyzer?error=Error exporting requests"})