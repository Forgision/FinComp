import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy import func, Column, JSON
from sqlalchemy.orm import Session
from sqlmodel import Field, SQLModel, select

logger = logging.getLogger(__name__)

class OrderLatency(SQLModel, table=True):
    """Model for tracking end-to-end order execution latency"""
    __tablename__ = 'order_latency'

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})
    order_id: str = Field(max_length=100)
    user_id: Optional[int] = Field(default=None)
    broker: Optional[str] = Field(default=None, max_length=50)
    symbol: Optional[str] = Field(default=None, max_length=50)
    order_type: Optional[str] = Field(default=None, max_length=20)

    rtt_ms: Optional[float] = Field(default=None)
    validation_latency_ms: Optional[float] = Field(default=None)
    response_latency_ms: Optional[float] = Field(default=None)
    overhead_ms: Optional[float] = Field(default=None)
    total_latency_ms: float

    request_body: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    response_body: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    status: Optional[str] = Field(default=None, max_length=20)
    error: Optional[str] = Field(default=None, max_length=500)


def log_latency(
    db: Session,
    order_id: str,
    user_id: int,
    broker: str,
    symbol: str,
    order_type: str,
    latencies: Dict[str, float],
    request_body: Dict[str, Any],
    response_body: Dict[str, Any],
    status: str,
    error: str = None
):
    """Log order execution latency"""
    try:
        log = OrderLatency(
            order_id=order_id,
            user_id=user_id,
            broker=broker,
            symbol=symbol,
            order_type=order_type,
            rtt_ms=latencies.get('rtt', 0),
            validation_latency_ms=latencies.get('validation', 0),
            response_latency_ms=latencies.get('broker_response', 0),
            overhead_ms=latencies.get('overhead', 0),
            total_latency_ms=latencies.get('total', 0),
            request_body=request_body,
            response_body=response_body,
            status=status,
            error=error
        )
        db.add(log)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error logging latency: {str(e)}")
        db.rollback()
        return False

def get_recent_logs(db: Session, limit: int = 100) -> List[OrderLatency]:
    """Get recent latency logs ordered by timestamp"""
    try:
        statement = select(OrderLatency).order_by(OrderLatency.timestamp.desc()).limit(limit)
        return db.exec(statement).all()
    except Exception as e:
        logger.error(f"Error getting recent latency logs: {str(e)}")
        return []

def get_latency_stats(db: Session) -> Dict[str, Any]:
    """Get latency statistics"""
    try:
        total_orders = db.exec(select(func.count(OrderLatency.id))).one()
        failed_orders = db.exec(select(func.count(OrderLatency.id)).where(OrderLatency.status == 'FAILED')).one()

        avg_rtt = db.exec(select(func.avg(OrderLatency.rtt_ms))).one() or 0
        avg_overhead = db.exec(select(func.avg(OrderLatency.overhead_ms))).one() or 0
        avg_total = db.exec(select(func.avg(OrderLatency.total_latency_ms))).one() or 0

        rtt_latencies = db.exec(select(OrderLatency.rtt_ms).where(OrderLatency.rtt_ms.isnot(None)).order_by(OrderLatency.rtt_ms)).all()

        p50_rtt = p90_rtt = p99_rtt = 0
        if rtt_latencies:
            p50_rtt = rtt_latencies[int(len(rtt_latencies) * 0.5)]
            p90_rtt = rtt_latencies[int(len(rtt_latencies) * 0.9)]
            p99_rtt = rtt_latencies[int(len(rtt_latencies) * 0.99)]

        broker_stats = {}
        brokers = db.exec(select(OrderLatency.broker).distinct()).all()

        for broker in [b for b in brokers if b]:
            total = db.exec(select(func.count(OrderLatency.id)).where(OrderLatency.broker == broker)).one()
            failed = db.exec(select(func.count(OrderLatency.id)).where(OrderLatency.broker == broker, OrderLatency.status == 'FAILED')).one()
            rtt = db.exec(select(func.avg(OrderLatency.rtt_ms)).where(OrderLatency.broker == broker)).one() or 0
            overhead = db.exec(select(func.avg(OrderLatency.overhead_ms)).where(OrderLatency.broker == broker)).one() or 0
            total_latency = db.exec(select(func.avg(OrderLatency.total_latency_ms)).where(OrderLatency.broker == broker)).one() or 0

            broker_stats[broker] = {
                'total_orders': total,
                'failed_orders': failed,
                'avg_rtt': float(rtt),
                'avg_overhead': float(overhead),
                'avg_total': float(total_latency)
            }

        return {
            'total_orders': total_orders, 'failed_orders': failed_orders,
            'avg_rtt': float(avg_rtt), 'avg_overhead': float(avg_overhead), 'avg_total': float(avg_total),
            'p50_rtt': float(p50_rtt), 'p90_rtt': float(p90_rtt), 'p99_rtt': float(p99_rtt),
            'broker_stats': broker_stats
        }
    except Exception as e:
        logger.error(f"Error getting latency stats: {str(e)}")
        return {
            'total_orders': 0, 'failed_orders': 0, 'avg_rtt': 0, 'avg_overhead': 0,
            'avg_total': 0, 'p50_rtt': 0, 'p90_rtt': 0, 'p99_rtt': 0, 'broker_stats': {}
        }
