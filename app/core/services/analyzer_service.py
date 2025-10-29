# app/core/services/analyzer_service.py

import csv
import io
import json
import traceback
from datetime import datetime, timedelta, tzinfo

import pytz
from sqlalchemy import func, select, delete
from sqlalchemy.orm import Session

from app.core.schemas.analyzer_db import AnalyzerLog
from app.core.schemas.settings_db import get_analyze_mode, set_analyze_mode
from app.utils.api_analyzer import get_analyzer_stats
from app.utils.logging import logger


async def get_analyzer_status(db: Session, analyzer_data: dict, api_key: str):
    """Get analyzer mode status and statistics"""
    try:
        is_enabled = get_analyze_mode(db)
        stats = get_analyzer_stats()
        response_data = {
            "status": "success",
            "mode": "analyze" if is_enabled else "live",
            "stats": stats
        }
        return True, response_data, 200
    except Exception as e:
        logger.error(f"Error getting analyzer status: {e}")
        return False, {"status": "error", "message": "Internal server error"}, 500


async def toggle_analyzer_mode(db: Session, analyzer_data: dict, api_key: str):
    """Toggle analyzer mode on/off"""
    try:
        current_mode = get_analyze_mode(db)
        new_mode = not current_mode
        set_analyze_mode(db, new_mode)
        response_data = {
            "status": "success",
            "message": f"Analyzer mode turned {'ON' if new_mode else 'OFF'}",
            "mode": "analyze" if new_mode else "live"
        }
        return True, response_data, 200
    except Exception as e:
        logger.error(f"Error toggling analyzer mode: {e}")
        return False, {"status": "error", "message": "Internal server error"}, 500


def format_request(req: AnalyzerLog, ist: tzinfo):
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
        stmt = select(AnalyzerLog).order_by(AnalyzerLog.created_at.desc()).limit(100)
        recent = db.execute(stmt).scalars().all()
        requests = []

        for req in recent:
            formatted = format_request(req, ist)
            if formatted:
                requests.append(formatted)

        return requests
    except Exception as e:
        logger.error(f"Error getting recent requests: {str(e)}")
        return []


def get_filtered_requests(db: Session, start_date=None, end_date=None):
    """Get analyzer requests with date filtering"""
    try:
        ist = pytz.timezone('Asia/Kolkata')
        stmt = select(AnalyzerLog)

        # Apply date filters if provided
        if start_date:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            stmt = stmt.where(func.date(AnalyzerLog.created_at) >= start_date)
        if end_date:
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            stmt = stmt.where(func.date(AnalyzerLog.created_at) <= end_date)

        # If no dates provided, default to today
        if not start_date and not end_date:
            today_ist = datetime.now(ist).date()
            stmt = stmt.where(func.date(AnalyzerLog.created_at) == today_ist)

        # Get results ordered by created_at
        results = db.execute(stmt.order_by(AnalyzerLog.created_at.desc())).scalars().all()
        requests = []

        for req in results:
            formatted = format_request(req, ist)
            if formatted:
                requests.append(formatted)

        return requests
    except Exception as e:
        logger.error(f"Error getting filtered requests: {str(e)}\n{traceback.format_exc()}")
        return []


def generate_csv(requests: list) -> str:
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


def clear_analyzer_logs(db: Session):
    """Clear analyzer logs"""
    try:
        # Delete all logs older than 24 hours
        cutoff = datetime.now(pytz.UTC) - timedelta(hours=24)
        stmt = delete(AnalyzerLog.__table__).where(AnalyzerLog.created_at < cutoff)
        db.execute(stmt)
        db.commit()
        return True, "Analyzer logs cleared successfully"
    except Exception as e:
        logger.error(f"Error clearing analyzer logs: {str(e)}")
        db.rollback()
        return False, "Error clearing analyzer logs"
