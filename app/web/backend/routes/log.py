# app/web/backend/routes/log.py

import io
import traceback
from datetime import date, datetime

import pytz
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas.apilog_db import OrderLog

# Assuming these imports will be available or need to be created/imported from other modules
from app.core.schemas import get_db
from app.utils.logging import logger
from app.utils.session import check_session_validity_fastapi
from app.utils.log_utils import format_log_entry, generate_csv

log_router = APIRouter(prefix="/logs", tags=["logs"])


# move to logs in db
async def get_filtered_logs(
    db: AsyncSession,
    start_date: date = None,
    end_date: date = None,
    search_query: str = None,
    page: int = None,
    per_page: int = None,
):
    """Get filtered logs with pagination"""
    ist = pytz.timezone("Asia/Kolkata")
    query = select(OrderLog)

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
                (OrderLog.api_type.ilike(search))
                | (OrderLog.request_data.ilike(search))
                | (OrderLog.response_data.ilike(search))
            )

        # Get total count
        total_logs = (
            await db.execute(select(func.count()).select_from(query.subquery()))
        ).scalar_one()

        # Calculate total pages only if pagination is enabled
        if page is not None and per_page is not None:
            total_pages = (total_logs + per_page - 1) // per_page
            # Apply pagination
            query = (
                query.order_by(OrderLog.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
        else:
            total_pages = 1
            query = query.order_by(OrderLog.created_at.desc())

        # Format logs
        logs = [
            format_log_entry(log, ist)
            for log in (await db.execute(query)).scalars().all()
        ]
        logger.info(f"Retrieved {len(logs)} logs")

        return logs, total_pages, total_logs

    except Exception as e:
        logger.error(f"Error in get_filtered_logs: {str(e)}\n{traceback.format_exc()}")
        return [], 1, 0


@log_router.get("/")
async def view_logs(
    request: Request,
    db: AsyncSession = Depends(get_db),
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
        logs, total_pages, _ = await get_filtered_logs(
            db=db,
            start_date=start_date,
            end_date=end_date,
            search_query=search,
            page=page,
            per_page=per_page,
        )

        # If AJAX request, return JSON
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse(
                {"logs": logs, "total_pages": total_pages, "current_page": page}
            )

        logger.info(f"Found {len(logs)} log entries")
        return JSONResponse(
            content={
                "logs": logs,
                "total_pages": total_pages,
                "current_page": page,
                "search_query": search,
                "start_date": start_date.strftime("%Y-%m-%d") if start_date else None,
                "end_date": end_date.strftime("%Y-%m-%d") if end_date else None,
            }
        )

    except Exception as e:
        logger.error(f"Error in view_logs: {str(e)}\n{traceback.format_exc()}")
        return JSONResponse(
            content={
                "logs": [],
                "total_pages": 1,
                "current_page": 1,
                "search_query": "",
                "start_date": None,
                "end_date": None,
                "error": str(e),
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@log_router.get("/export")
async def export_logs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_valid: bool = Depends(check_session_validity_fastapi),
    start_date: date = Query(None),
    end_date: date = Query(None),
    search: str = Query(None, alias="search_query"),
):
    try:
        logger.info("Starting log export")

        # Get parameters
        # FastAPI handles query parameters directly, no need for request.args.get
        logger.info(
            f"Export parameters - start_date: {start_date}, end_date: {end_date}, search: {search}"
        )

        # Get all logs without pagination
        logs, _, total = await get_filtered_logs(
            db=db,
            start_date=start_date,
            end_date=end_date,
            search_query=search,
            page=None,
            per_page=None,
        )

        logger.info(f"Retrieved {total} logs for export")

        # Generate CSV content
        csv_output = generate_csv(logs)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"openalgo_logs_{timestamp}.csv"

        logger.info(f"Generated CSV file: {filename}")

        return StreamingResponse(
            io.StringIO(csv_output),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv",
            },
        )

    except Exception as e:
        error_msg = f"Error exporting logs: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return JSONResponse({"error": error_msg}, status_code=500)
