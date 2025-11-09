import io

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.schemas.latency_db import (
    OrderLatency,
    get_recent_logs,
    get_latency_stats,
    get_histogram_data,
)
from app.core.schemas import get_db
from app.utils.logging import logger
from app.utils.session import check_session_validity_fastapi
from app.utils.web.limiter import limiter
from app.utils.time_utils import convert_to_ist, format_ist_time
from app.utils.latency_utils import generate_csv

latency_router = APIRouter(prefix="/latency", tags=["Latency"])


@latency_router.get("/", dependencies=[Depends(check_session_validity_fastapi)])
@limiter.limit("60/minute")
async def latency_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """Display latency monitoring dashboard"""
    stats = await OrderLatency.get_latency_stats(db)
    recent_logs = await OrderLatency.get_recent_logs(db, limit=100)

    # Get histogram data for each broker
    broker_histograms = {}
    brokers = [
        b[0]
        for b in (await db.execute(select(OrderLatency.broker).distinct()))
        .scalars()
        .all()
    ]
    for broker in brokers:
        if broker:  # Skip None values
            broker_histograms[broker] = await get_histogram_data(db, broker)

    # Format timestamps in IST
    for log in recent_logs:
        log.formatted_timestamp = format_ist_time(log.timestamp)

    return JSONResponse(
        content={
            "stats": stats,
            "logs": [
                {
                    "timestamp": convert_to_ist(log.timestamp).isoformat(),
                    "id": log.id,
                    "order_id": log.order_id,
                    "broker": log.broker,
                    "symbol": log.symbol,
                    "order_type": log.order_type,
                    "rtt_ms": log.rtt_ms,
                    "validation_latency_ms": log.validation_latency_ms,
                    "response_latency_ms": log.response_latency_ms,
                    "overhead_ms": log.overhead_ms,
                    "total_latency_ms": log.total_latency_ms,
                    "status": log.status,
                    "error": log.error,
                }
                for log in recent_logs
            ],
            "broker_histograms": broker_histograms,
        }
    )


@latency_router.get("/api/logs", dependencies=[Depends(check_session_validity_fastapi)])
@limiter.limit("60/minute")
async def get_logs(
    request: Request, db: AsyncSession = Depends(get_db), limit: int = 100
):
    """API endpoint to get latency logs"""
    try:
        limit = min(limit, 1000)
        logs = await get_recent_logs(db, limit=limit)
        return JSONResponse(
            [
                {
                    "timestamp": convert_to_ist(log.timestamp).isoformat(),
                    "id": log.id,
                    "order_id": log.order_id,
                    "broker": log.broker,
                    "symbol": log.symbol,
                    "order_type": log.order_type,
                    "rtt_ms": log.rtt_ms,
                    "validation_latency_ms": log.validation_latency_ms,
                    "response_latency_ms": log.response_latency_ms,
                    "overhead_ms": log.overhead_ms,
                    "total_latency_ms": log.total_latency_ms,
                    "status": log.status,
                    "error": log.error,
                }
                for log in logs
            ]
        )
    except Exception as e:
        logger.error(f"Error fetching latency logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@latency_router.get(
    "/api/stats", dependencies=[Depends(check_session_validity_fastapi)]
)
@limiter.limit("60/minute")
async def get_stats(request: Request, db: AsyncSession = Depends(get_db)):
    """API endpoint to get latency statistics"""
    try:
        stats = await OrderLatency.get_latency_stats(db)

        # Add histogram data for each broker
        broker_histograms = {}
        for broker in stats.get("broker_stats", {}):
            broker_histograms[broker] = await get_histogram_data(db, broker)

        stats["broker_histograms"] = broker_histograms
        return JSONResponse(stats)
    except Exception as e:
        logger.error(f"Error fetching latency stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@latency_router.get(
    "/api/broker/{broker}/stats", dependencies=[Depends(check_session_validity_fastapi)]
)
@limiter.limit("60/minute")
async def get_broker_stats(
    request: Request, broker: str, db: AsyncSession = Depends(get_db)
):
    """API endpoint to get broker-specific latency statistics"""
    try:
        stats = await get_latency_stats(db)
        broker_stats = stats.get("broker_stats", {}).get(broker, {})
        if not broker_stats:
            raise HTTPException(status_code=404, detail="Broker not found")

        # Add histogram data
        broker_stats["histogram"] = await get_histogram_data(db, broker)
        return JSONResponse(broker_stats)
    except Exception as e:
        logger.error(f"Error fetching broker stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@latency_router.get("/export", dependencies=[Depends(check_session_validity_fastapi)])
@limiter.limit("10/minute")
async def export_logs(request: Request, db: AsyncSession = Depends(get_db)):
    """Export latency logs to CSV"""
    try:
        # Get all logs for the current day
        logs = await get_recent_logs(db, limit=None)  # None to get all logs

        # Generate CSV
        csv_data = generate_csv(logs)

        return StreamingResponse(
            io.BytesIO(csv_data.encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=latency_logs.csv"},
        )

    except Exception as e:
        logger.error(f"Error exporting latency logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
