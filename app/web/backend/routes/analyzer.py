import traceback
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import get_db
from app.core.services import analyzer_service
from app.utils.api_analyzer import get_analyzer_stats
from app.utils.logging import logger
from app.utils.session import check_session_validity_fastapi

analyzer_router = APIRouter(prefix="/analyzer", tags=["analyzer"])


async def get_current_user(user: str = Depends(check_session_validity_fastapi)):
    return user


@analyzer_router.get("/")
async def analyzer(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
    start_date: str = None,
    end_date: str = None,
):
    """Render the analyzer dashboard"""
    try:
        # Get stats with proper structure
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

        # Get filtered requests
        requests = await analyzer_service.get_filtered_requests(db, start_date, end_date)

        return JSONResponse(
            content={
                "requests": requests,
                "stats": stats,
                "start_date": start_date,
                "end_date": end_date,
                "current_user": current_user,
            }
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error rendering analyzer: {str(e)}\n{traceback.format_exc()}")
        # FastAPI doesn't have flash messages like Flask.
        # You might want to add a dependency for flash messages or handle errors differently.
        return JSONResponse(
            content={"message": "Error loading analyzer dashboard"}, status_code=500
        )


@analyzer_router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db), current_user: str = Depends(get_current_user)
):
    """Get analyzer stats endpoint"""
    try:
        stats = await get_analyzer_stats(db)
        return JSONResponse(stats)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error getting analyzer stats: {str(e)}")
        return JSONResponse(
            {
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
            },
            status_code=500,
        )


@analyzer_router.get("/requests")
async def get_requests(
    db: AsyncSession = Depends(get_db), current_user: str = Depends(get_current_user)
):
    """Get analyzer requests endpoint"""
    try:
        requests = await analyzer_service.get_recent_requests(db)
        return JSONResponse({"requests": requests})
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error getting analyzer requests: {str(e)}")
        return JSONResponse({"requests": []}, status_code=500)


@analyzer_router.get("/clear")
async def clear_logs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Clear analyzer logs"""
    try:
        await analyzer_service.clear_analyzer_logs(db)
        # In FastAPI, you might use a redirect with a query parameter for a message, or a dedicated flash message system
        return Response(
            status_code=303,
            headers={"Location": "/analyzer?message=Logs cleared successfully"},
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error clearing analyzer logs: {str(e)}")
        return Response(
            status_code=303, headers={"Location": "/analyzer?error=Error clearing logs"}
        )


@analyzer_router.get("/export")
async def export_requests(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
    start_date: str = None,
    end_date: str = None,
):
    """Export analyzer requests to CSV"""
    try:
        # Get filtered requests
        requests = await analyzer_service.get_filtered_requests(db, start_date, end_date)

        # Generate CSV
        csv_data = analyzer_service.generate_csv(requests)

        # Create the response
        response = Response(content=csv_data, media_type="text/csv")
        response.headers["Content-Disposition"] = (
            f"attachment; filename=analyzer_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        return response
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error exporting requests: {str(e)}\n{traceback.format_exc()}")
        return Response(
            status_code=303,
            headers={"Location": "/analyzer?error=Error exporting requests"},
        )
