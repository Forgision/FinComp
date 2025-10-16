# app/web/backend/routes/log.py

from fastapi import APIRouter, Depends, Request, Query, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
import pytz
from datetime import datetime, date
import json
import csv
import io
import traceback

# Assuming these imports will be available or need to be created/imported from other modules
from app.db.session import get_db
from app.utils.session import check_session_validity_fastapi # This will be a FastAPI dependency
from app.db.apilog_db import OrderLog # Adjusted import path
from app.core.config import settings # For template directory
from app.utils.logging import logger
from app.web.frontend import templates

log_router = APIRouter(prefix="/logs", tags=["logs"])

#TODO: move to utils
def sanitize_request_data(data):
    """Remove sensitive information from request data"""
    try:
        if isinstance(data, str):
            data = json.loads(data)
        if isinstance(data, dict):
            # Create a copy to avoid modifying the original
            sanitized = data.copy()
            # Remove apikey if present
            sanitized.pop('apikey', None)
            return sanitized
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON: {data}")
        return {}
    except Exception as e:
        logger.error(f"Error sanitizing data: {str(e)}")
        return {}
    return data

# move to logs in db
def format_log_entry(log, ist):
    """Format a single log entry"""
    try:
        request_data = sanitize_request_data(log.request_data)
        try:
            response_data = json.loads(log.response_data) if log.response_data else {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding response JSON for log {log.id}")
            response_data = {}
        except Exception as e:
            logger.error(f"Error processing response data for log {log.id}: {str(e)}")
            response_data = {}
        
        # Extract strategy from request data
        strategy = request_data.get('strategy', 'Unknown') if isinstance(request_data, dict) else 'Unknown'
        
        return {
            'id': log.id,
            'api_type': log.api_type,
            'request_data': request_data,
            'response_data': response_data,
            'strategy': strategy,
            'created_at': log.created_at.astimezone(ist).strftime('%Y-%m-%d %I:%M:%S %p')
        }
    except Exception as e:
        logger.error(f"Error formatting log {log.id}: {str(e)}\n{traceback.format_exc()}")
        return {
            'id': log.id,
            'api_type': log.api_type,
            'request_data': {},
            'response_data': {},
            'strategy': 'Unknown',
            'created_at': log.created_at.astimezone(ist).strftime('%Y-%m-%d %I:%M:%S %p')
        }

# move to logs in db
def get_filtered_logs(db: Session, start_date: date = None, end_date: date = None, search_query: str = None, page: int = None, per_page: int = None):
    """Get filtered logs with pagination"""
    ist = pytz.timezone('Asia/Kolkata')
    query = db.query(OrderLog) # Use db.query instead of OrderLog.query

    try:
        # Apply date filters if provided
        if start_date:
            query = query.filter(func.date(OrderLog.created_at) >= start_date)
        if end_date:
            query = query.filter(func.date(OrderLog.created_at) <= end_date)
        
        # If no dates provided, default to today
        if not start_date and not end_date:
            today_ist = datetime.now(ist).date()
            query = query.filter(func.date(OrderLog.created_at) == today_ist)

        # Apply search filter if provided
        if search_query:
            search = f"%{search_query}%"
            query = query.filter(
                (OrderLog.api_type.ilike(search)) |
                (OrderLog.request_data.ilike(search)) |
                (OrderLog.response_data.ilike(search))
            )

        # Get total count
        total_logs = query.count()

        # Calculate total pages only if pagination is enabled
        if page is not None and per_page is not None:
            total_pages = (total_logs + per_page - 1) // per_page
            # Apply pagination
            query = query.order_by(OrderLog.created_at.desc())\
                       .offset((page - 1) * per_page)\
                       .limit(per_page)
        else:
            total_pages = 1
            query = query.order_by(OrderLog.created_at.desc())

        # Format logs
        logs = [format_log_entry(log, ist) for log in query.all()]
        logger.info(f"Retrieved {len(logs)} logs")

        return logs, total_pages, total_logs

    except Exception as e:
        logger.error(f"Error in get_filtered_logs: {str(e)}\n{traceback.format_exc()}")
        return [], 1, 0

# move to logs in db
def generate_csv(logs):
    """Generate CSV file from logs"""
    try:
        si = io.StringIO()
        writer = csv.writer(si)
        
        # Write headers - include all possible fields from all request types
        headers = [
            'ID', 
            'Timestamp', 
            'API Type', 
            'Strategy',
            'Exchange',
            'Symbol',
            'Action',
            'Product',
            'Price Type',
            'Quantity',
            'Position Size',  # For placesmartorder
            'Price',
            'Trigger Price',
            'Disclosed Quantity',
            'Order ID',  # For modifyorder, cancelorder
            'Response'
        ]
        writer.writerow(headers)
        
        # Write data
        for log in logs:
            try:
                request_data = log['request_data']
                if not isinstance(request_data, dict):
                    request_data = {}
                
                # Format response data for CSV
                response_data = log['response_data']
                if isinstance(response_data, dict):
                    response_str = json.dumps(response_data)
                else:
                    response_str = str(response_data)
                
                # Build row with all possible fields
                row = [
                    log['id'],
                    log['created_at'],
                    log['api_type'],
                    log['strategy'],
                    request_data.get('exchange', ''),
                    request_data.get('symbol', ''),
                    request_data.get('action', ''),
                    request_data.get('product', ''),
                    request_data.get('pricetype', ''),
                    request_data.get('quantity', ''),
                    request_data.get('position_size', ''),  # Only for placesmartorder
                    request_data.get('price', ''),
                    request_data.get('trigger_price', ''),
                    request_data.get('disclosed_quantity', ''),
                    request_data.get('orderid', ''),  # For modifyorder, cancelorder
                    response_str
                ]
                writer.writerow(row)
                logger.debug(f"Wrote row: {row}")
            except Exception as e:
                logger.error(f"Error writing row for log {log.get('id')}: {str(e)}")
                continue
        
        return si.getvalue()

    except Exception as e:
        logger.error(f"Error generating CSV: {str(e)}\n{traceback.format_exc()}")
        raise


@log_router.get("/")
async def view_logs(
    request: Request,
    db: Session = Depends(get_db),
    # The check_session_validity_fastapi dependency will handle session validation
    # and potentially redirect if not valid.
    # For now, let's assume it works as a dependency that raises HTTPException on failure.
    session_valid: bool = Depends(check_session_validity_fastapi),
    start_date: date = Query(None),
    end_date: date = Query(None),
    search: str = Query(None, alias="search_query"),
    page: int = Query(1),
):
    try:
        per_page = 20

        # Get filtered logs
        logs, total_pages, _ = get_filtered_logs(
            db=db,
            start_date=start_date,
            end_date=end_date,
            search_query=search,
            page=page,
            per_page=per_page
        )

        # If AJAX request, return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JSONResponse({
                'logs': logs,
                'total_pages': total_pages,
                'current_page': page
            })

        logger.info(f"Found {len(logs)} log entries")
        return templates.TemplateResponse(
            "logs.html",
            {
                "request": request,
                "logs": logs,
                "total_pages": total_pages,
                "current_page": page,
                "search_query": search,
                "start_date": start_date.strftime('%Y-%m-%d') if start_date else None,
                "end_date": end_date.strftime('%Y-%m-%d') if end_date else None,
            },
        )
        
    except Exception as e:
        logger.error(f"Error in view_logs: {str(e)}\n{traceback.format_exc()}")
        return templates.TemplateResponse(
            "logs.html",
            {
                "request": request,
                "logs": [],
                "total_pages": 1,
                "current_page": 1,
                "search_query": "",
                "start_date": None,
                "end_date": None,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@log_router.get("/export")
async def export_logs(
    request: Request,
    db: Session = Depends(get_db),
    session_valid: bool = Depends(check_session_validity_fastapi),
    start_date: date = Query(None),
    end_date: date = Query(None),
    search: str = Query(None, alias="search_query"),
):
    try:
        logger.info("Starting log export")
        
        # Get parameters
        # FastAPI handles query parameters directly, no need for request.args.get
        logger.info(f"Export parameters - start_date: {start_date}, end_date: {end_date}, search: {search}")

        # Get all logs without pagination
        logs, _, total = get_filtered_logs(
            db=db,
            start_date=start_date,
            end_date=end_date,
            search_query=search,
            page=None,
            per_page=None
        )

        logger.info(f"Retrieved {total} logs for export")

        # Generate CSV content
        csv_output = generate_csv(logs)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'openalgo_logs_{timestamp}.csv'

        logger.info(f"Generated CSV file: {filename}")

        return StreamingResponse(
            io.StringIO(csv_output),
            media_type='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'text/csv'
            }
        )

    except Exception as e:
        error_msg = f"Error exporting logs: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return JSONResponse({'error': error_msg}, status_code=500)