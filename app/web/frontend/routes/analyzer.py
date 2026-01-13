from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import get_db
from app.core.services import analyzer_service
from app.utils.api_analyzer import get_analyzer_stats
from app.utils.session import check_session_validity_fastapi

analyzer_router = APIRouter()
templates = Jinja2Templates(directory="app/frontend/templates")


@analyzer_router.get("/", response_class=HTMLResponse)
async def analyzer(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(check_session_validity_fastapi),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/", status_code=302)

    try:
        stats = await get_analyzer_stats(db)
        if not isinstance(stats, dict):
            stats = {
                "total_requests": 0,
                "sources": {},
                "symbols": [],
                "issues": {
                    "total": 0,
                    "by_type": {
                        "rate_limit": 0,
                        "invalid_symbol": 0,
                        "missing_quantity": 0,
                        "invalid_exchange": 0,
                        "other": 0,
                    },
                },
            }

        requests_data = await analyzer_service.get_filtered_requests(db, start_date, end_date)

        return templates.TemplateResponse(
            "analyzer.html",
            {
                "request": request,
                "requests": requests_data,
                "stats": stats,
                "start_date": start_date,
                "end_date": end_date,
                "current_user": current_user,
            },
        )
    except Exception:
        # In a real app, you'd have a proper error handling middleware
        # For now, just return a simple error response
        return RedirectResponse(url="/", status_code=302)


@analyzer_router.get("/stats")
async def get_stats(
    current_user: dict = Depends(check_session_validity_fastapi),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
    try:
        stats = await get_analyzer_stats(db)
        return JSONResponse(content=stats)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@analyzer_router.get("/requests")
async def get_requests(
    current_user: dict = Depends(check_session_validity_fastapi),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
    try:
        requests_data = await analyzer_service.get_recent_requests(db)
        return JSONResponse(content={"requests": requests_data})
    except Exception as e:
        return JSONResponse(content={"requests": [], "error": str(e)}, status_code=500)


@analyzer_router.get("/clear")
async def clear_logs(
    current_user: dict = Depends(check_session_validity_fastapi),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/", status_code=302)

    success, message = await analyzer_service.clear_analyzer_logs(db)
    # FastAPI doesn't have a built-in flash mechanism like Flask.
    # This would typically be handled on the client-side or with session middleware.
    return RedirectResponse(url="/analyzer", status_code=302)


@analyzer_router.get("/export")
async def export_requests(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(check_session_validity_fastapi),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        return Response("Unauthorized", status_code=401)

    try:
        requests_data = await analyzer_service.get_filtered_requests(db, start_date, end_date)
        csv_data = analyzer_service.generate_csv(requests_data)
        filename = f"analyzer_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception:
        return RedirectResponse(url="/analyzer", status_code=302)
