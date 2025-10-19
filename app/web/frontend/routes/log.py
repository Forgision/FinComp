import json
import traceback
from datetime import datetime
from typing import Optional

import pytz
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from app.db.models.apilog_db import OrderLog
from app.db.models.session import get_db
from app.utils.logging import get_logger
from app.utils.session import check_session_validity_fastapi

logger = get_logger(__name__)
templates = Jinja2Templates(directory="app/frontend/templates")

log_router = APIRouter(prefix="/logs")

def sanitize_request_data(data):
    try:
        if isinstance(data, str):
            data = json.loads(data)
        if isinstance(data, dict):
            sanitized = data.copy()
            sanitized.pop('apikey', None)
            return sanitized
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Error sanitizing data: {e}")
    return {}

def format_log_entry(log, ist):
    try:
        request_data = sanitize_request_data(log.request_data)
        response_data = json.loads(log.response_data) if log.response_data else {}
        strategy = request_data.get('strategy', 'Unknown') if isinstance(request_data, dict) else 'Unknown'
        return {
            'id': log.id, 'api_type': log.api_type, 'request_data': request_data,
            'response_data': response_data, 'strategy': strategy,
            'created_at': log.created_at.astimezone(ist).strftime('%Y-%m-%d %I:%M:%S %p')
        }
    except Exception as e:
        logger.error(f"Error formatting log {log.id}: {e}\n{traceback.format_exc()}")
        return {'id': log.id, 'api_type': log.api_type, 'request_data': {}, 'response_data': {},
                'strategy': 'Unknown', 'created_at': 'Error'}

def get_filtered_logs(db: Session, start_date=None, end_date=None, search_query=None, page=None, per_page=None):
    ist = pytz.timezone('Asia/Kolkata')
    query = db.query(OrderLog)
    try:
        if start_date:
            query = query.filter(func.date(OrderLog.created_at) >= start_date)
        if end_date:
            query = query.filter(func.date(OrderLog.created_at) <= end_date)
        if not start_date and not end_date:
            today_ist = datetime.now(ist).date()
            query = query.filter(func.date(OrderLog.created_at) == today_ist)
        if search_query:
            search = f"%{search_query}%"
            query = query.filter((OrderLog.api_type.ilike(search)) | (OrderLog.request_data.ilike(search)) | (OrderLog.response_data.ilike(search)))
        
        total_logs = query.count()
        
        if page and per_page:
            total_pages = (total_logs + per_page - 1) // per_page
            query = query.order_by(OrderLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
        else:
            total_pages = 1
            query = query.order_by(OrderLog.created_at.desc())
            
        logs = [format_log_entry(log, ist) for log in query.all()]
        return logs, total_pages, total_logs
    except Exception as e:
        logger.error(f"Error in get_filtered_logs: {e}\n{traceback.format_exc()}")
        return [], 1, 0

@log_router.get("/", dependencies=[Depends(check_session_validity_fastapi)])
async def view_logs(request: Request, db: Session = Depends(get_db),
                    start_date: Optional[str] = Query(None), end_date: Optional[str] = Query(None),
                    search: Optional[str] = Query(None), page: int = 1):
    try:
        logs, total_pages, _ = get_filtered_logs(
            db, start_date=start_date, end_date=end_date, search_query=search, page=page, per_page=20
        )
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse({'logs': logs, 'total_pages': total_pages, 'current_page': page})
        
        return templates.TemplateResponse("logs.html", {
            "request": request, "logs": logs, "total_pages": total_pages, "current_page": page,
            "search_query": search, "start_date": start_date, "end_date": end_date
        })
    except Exception as e:
        logger.error(f"Error in view_logs: {e}\n{traceback.format_exc()}")
        return templates.TemplateResponse("logs.html", {"request": request, "logs": [], "total_pages": 1, "current_page": 1})

# ... other routes can be refactored similarly