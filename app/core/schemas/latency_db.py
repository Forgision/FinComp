import os

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

import numpy as np

from app.core.config import settings
from app.utils.logging import logger
from app.core.schemas import DBConnectionConfig, make_db_connection, INIT_DB_REGISTRY


# Use a separate database for latency logs
LATENCY_DATABASE_URL = settings.LATENCY_DATABASE_URL


latency_db_config = DBConnectionConfig(
    database_url=settings.LATENCY_DATABASE_URL,
    echo=False,
)


latency_engine, latency_session, get_latency_db = make_db_connection(latency_db_config)


class LatencyBase(DeclarativeBase):
    pass


class OrderLatency(LatencyBase):
    """Model for tracking end-to-end order execution latency"""

    __tablename__ = "order_latency"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    order_id = Column(String(100), nullable=False)
    user_id = Column(Integer)
    broker = Column(String(50))
    symbol = Column(String(50))
    order_type = Column(String(20))  # MARKET, LIMIT, etc.

    # Round-trip time (comparable to Postman/Bruno)
    rtt_ms = Column(Float)

    # Our processing overhead
    validation_latency_ms = Column(Float)  # Pre-request processing
    response_latency_ms = Column(Float)  # Post-response processing
    overhead_ms = Column(Float)  # Total overhead

    # Total time including overhead
    total_latency_ms = Column(Float, nullable=False)

    # Request details
    request_body = Column(JSON)  # Original request
    response_body = Column(JSON)  # Broker response
    status = Column(String(20))  # SUCCESS, FAILED, PARTIAL
    error = Column(String(500))  # Error message if any


async def init_latency_db():
    """Initialize the latency database"""
    # Extract directory from app.core.schemas URL and create if it doesn't exist
    db_path = LATENCY_DATABASE_URL.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    logger.info(f"Initializing Latency DB at: {LATENCY_DATABASE_URL}")

    # Create tables
    async with latency_engine.begin() as conn:
        await conn.run_sync(LatencyBase.metadata.create_all)


INIT_DB_REGISTRY["latency_db"] = init_latency_db


async def log_latency(
    order_id,
    user_id,
    broker,
    symbol,
    order_type,
    latencies,
    request_body,
    response_body,
    status,
    error=None,
):
    """Log order execution latency"""
    try:
        log = OrderLatency(
            order_id=order_id,
            user_id=user_id,
            broker=broker,
            symbol=symbol,
            order_type=order_type,
            rtt_ms=latencies.get("rtt", 0),
            validation_latency_ms=latencies.get("validation", 0),
            response_latency_ms=latencies.get("broker_response", 0),
            overhead_ms=latencies.get("overhead", 0),
            total_latency_ms=latencies.get("total", 0),
            request_body=request_body,
            response_body=response_body,
            status=status,
            error=error,
        )
        async with latency_session() as session:
            session.add(log)
            await session.commit()
            return True
    except Exception as e:
        logger.error(f"Error logging latency: {str(e)}")
        return False


async def get_recent_logs(limit=100):
    """Get recent latency logs ordered by timestamp"""
    try:
        async with latency_session() as session:
            result = await session.execute(
                select(OrderLatency)
                .order_by(OrderLatency.timestamp.desc())
                .limit(limit)
            )
            return result.scalars().all()
    except Exception as e:
        logger.error(f"Error getting recent latency logs: {str(e)}")
        return []


async def get_latency_stats():
    """Get latency statistics"""
    try:
        from sqlalchemy import func

        async with latency_session() as session:
            # Overall stats
            total_orders_result = await session.execute(
                select(func.count(OrderLatency.id))
            )
            total_orders = total_orders_result.scalar_one()

            failed_orders_result = await session.execute(
                select(func.count(OrderLatency.id)).where(
                    OrderLatency.status == "FAILED"
                )
            )
            failed_orders = failed_orders_result.scalar_one()

            # Get average latencies
            avg_rtt_result = await session.execute(
                select(func.avg(OrderLatency.rtt_ms))
            )
            avg_rtt = avg_rtt_result.scalar_one() or 0

            avg_overhead_result = await session.execute(
                select(func.avg(OrderLatency.overhead_ms))
            )
            avg_overhead = avg_overhead_result.scalar_one() or 0

            avg_total_result = await session.execute(
                select(func.avg(OrderLatency.total_latency_ms))
            )
            avg_total = avg_total_result.scalar_one() or 0

            # Get p50, p90, p99 latencies for RTT
            rtt_latencies_result = await session.execute(select(OrderLatency.rtt_ms))
            rtt_latencies = sorted(
                [r for r in rtt_latencies_result.scalars().all() if r is not None]
            )

            p50_rtt = p90_rtt = p99_rtt = 0
            if rtt_latencies:
                p50_rtt = rtt_latencies[int(len(rtt_latencies) * 0.5)]
                p90_rtt = rtt_latencies[int(len(rtt_latencies) * 0.9)]
                p99_rtt = rtt_latencies[int(len(rtt_latencies) * 0.99)]

            # Breakdown by broker using GROUP BY
            broker_stats_query = select(
                OrderLatency.broker,
                func.count(OrderLatency.id).label("total_orders"),
                func.count(OrderLatency.id)
                .filter(OrderLatency.status == "FAILED")
                .label("failed_orders"),
                func.avg(OrderLatency.rtt_ms).label("avg_rtt"),
                func.avg(OrderLatency.overhead_ms).label("avg_overhead"),
                func.avg(OrderLatency.total_latency_ms).label("avg_total"),
            ).group_by(OrderLatency.broker)

            broker_stats_result = await session.execute(broker_stats_query)
            broker_stats = {}
            for row in broker_stats_result:
                broker_name = row.broker
                if broker_name:
                    broker_stats[broker_name] = {
                        "total_orders": row.total_orders,
                        "failed_orders": row.failed_orders,
                        "avg_rtt": float(row.avg_rtt or 0),
                        "avg_overhead": float(row.avg_overhead or 0),
                        "avg_total": float(row.avg_total or 0),
                    }

            return {
                "total_orders": total_orders,
                "failed_orders": failed_orders,
                "avg_rtt": float(avg_rtt),
                "avg_overhead": float(avg_overhead),
                "avg_total": float(avg_total),
                "p50_rtt": float(p50_rtt),
                "p90_rtt": float(p90_rtt),
                "p99_rtt": float(p99_rtt),
                "broker_stats": broker_stats,
            }
    except Exception as e:
        logger.error(f"Error getting latency stats: {str(e)}")
        return {
            "total_orders": 0,
            "failed_orders": 0,
            "avg_rtt": 0,
            "avg_overhead": 0,
            "avg_total": 0,
            "p50_rtt": 0,
            "p90_rtt": 0,
            "p99_rtt": 0,
            "broker_stats": {},
        }


async def get_histogram_data(db: AsyncSession, broker: str = None):
    """Get histogram data for RTT distribution"""
    try:
        query = select(OrderLatency.rtt_ms)
        if broker:
            query = query.filter(OrderLatency.broker == broker)

        # Get all RTT values
        rtts = [r[0] for r in (await db.execute(query)).scalars().all()]

        if not rtts:
            return {"bins": [], "counts": [], "avg_rtt": 0, "min_rtt": 0, "max_rtt": 0}

        # Calculate statistics
        avg_rtt = sum(rtts) / len(rtts)
        min_rtt = min(rtts)
        max_rtt = max(rtts)

        # Create histogram bins
        bin_count = 30  # Number of bins

        # Create histogram using numpy
        counts, bins = np.histogram(rtts, bins=bin_count, range=(min_rtt, max_rtt))

        # Convert to list for JSON serialization
        counts = counts.tolist()
        bins = bins.tolist()

        # Create bin labels (use the start of each bin)
        bin_labels = [f"{bins[i]:.1f}" for i in range(len(bins) - 1)]

        data = {
            "bins": bin_labels,
            "counts": counts,
            "avg_rtt": float(avg_rtt),
            "min_rtt": float(min_rtt),
            "max_rtt": float(max_rtt),
        }

        return data

    except Exception as e:
        logger.error(f"Error getting histogram data: {e}")
        return {"bins": [], "counts": [], "avg_rtt": 0, "min_rtt": 0, "max_rtt": 0}
