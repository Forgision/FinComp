import logging
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession

from . import Base

logger = logging.getLogger(__name__)


class MasterContractStatus(Base):
    __tablename__ = "master_contract_status"

    broker: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    message: Mapped[str] = mapped_column(String)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    total_symbols: Mapped[str] = mapped_column(String, default="0")
    is_ready: Mapped[bool] = mapped_column(Boolean, default=False)


async def init_broker_status(db: AsyncSession, broker: str):
    """Initialize status for a broker when they login"""
    try:
        # Check if status already exists
        stmt = select(MasterContractStatus).filter_by(broker=broker)
        existing = await db.execute(stmt).scalars().first()

        if existing:
            # Update existing status
            existing.status = "pending"
            existing.message = "Master contract download pending"
            existing.last_updated = datetime.now()
            existing.is_ready = False
        else:
            # Create new status
            status = MasterContractStatus(
                broker=broker,
                status="pending",
                message="Master contract download pending",
                last_updated=datetime.now(),
                is_ready=False,
            )
            db.add(status)

        await db.commit()
        logger.info(f"Initialized master contract status for {broker}")

    except Exception as e:
        logger.error(f"Error initializing status for {broker}: {str(e)}")
        await db.rollback()


async def update_status(
    db: AsyncSession, broker: str, status: str, message: str, total_symbols: str = None
):
    """Update the download status for a broker"""
    try:
        stmt = select(MasterContractStatus).filter_by(broker=broker)
        broker_status = await db.execute(stmt).scalars().first()

        if broker_status:
            broker_status.status = status
            broker_status.message = message
            broker_status.last_updated = datetime.now()
            broker_status.is_ready = status == "success"

            if total_symbols is not None:
                broker_status.total_symbols = str(total_symbols)
        else:
            # Create new status if it doesn't exist
            broker_status = MasterContractStatus(
                broker=broker,
                status=status,
                message=message,
                last_updated=datetime.now(),
                is_ready=(status == "success"),
                total_symbols=str(total_symbols) if total_symbols else "0",
            )
            db.add(broker_status)

        await db.commit()
        logger.info(f"Updated master contract status for {broker}: {status}")

    except Exception as e:
        logger.error(f"Error updating status for {broker}: {str(e)}")
        await db.rollback()


async def get_status(db: AsyncSession, broker: str):
    """Get the current status for a broker"""
    try:
        stmt = select(MasterContractStatus).filter_by(broker=broker)
        status = await db.execute(stmt).scalars().first()

        if status:
            return {
                "broker": status.broker,
                "status": status.status,
                "message": status.message,
                "last_updated": (
                    status.last_updated.isoformat() if status.last_updated else None
                ),
                "total_symbols": status.total_symbols,
                "is_ready": status.is_ready,
            }
        else:
            return {
                "broker": broker,
                "status": "unknown",
                "message": "No status available",
                "last_updated": None,
                "total_symbols": "0",
                "is_ready": False,
            }
    except Exception as e:
        logger.error(f"Error getting status for {broker}: {str(e)}")
        return {
            "broker": broker,
            "status": "error",
            "message": f"Error retrieving status: {str(e)}",
            "last_updated": None,
            "total_symbols": "0",
            "is_ready": False,
        }


async def check_if_ready(db: AsyncSession, broker: str):
    """Check if master contracts are ready for a broker"""
    try:
        stmt = select(MasterContractStatus).filter_by(broker=broker)
        status = await db.execute(stmt).scalars().first()
        return status.is_ready if status else False
    except Exception as e:
        logger.error(f"Error checking if ready for {broker}: {str(e)}")
        return False
