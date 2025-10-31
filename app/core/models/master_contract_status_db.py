import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlmodel import Field, SQLModel, select

logger = logging.getLogger(__name__)

class MasterContractStatus(SQLModel, table=True):
    __tablename__ = 'master_contract_status'

    broker: str = Field(primary_key=True, max_length=255)
    status: str = Field(default='pending', max_length=255)
    message: str
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    total_symbols: str = Field(default='0')
    is_ready: bool = Field(default=False)


def init_broker_status(db: Session, broker: str):
    """Initialize status for a broker when they login"""
    try:
        existing = db.get(MasterContractStatus, broker)

        if existing:
            existing.status = 'pending'
            existing.message = 'Master contract download pending'
            existing.last_updated = datetime.now()
            existing.is_ready = False
            db.add(existing)
        else:
            status = MasterContractStatus(
                broker=broker,
                status='pending',
                message='Master contract download pending',
                last_updated=datetime.now(),
                is_ready=False
            )
            db.add(status)

        db.commit()
        logger.info(f"Initialized master contract status for {broker}")

    except Exception as e:
        logger.error(f"Error initializing status for {broker}: {str(e)}")
        db.rollback()

def update_status(db: Session, broker: str, status: str, message: str, total_symbols: Optional[int] = None):
    """Update the download status for a broker"""
    try:
        broker_status = db.get(MasterContractStatus, broker)

        if broker_status:
            broker_status.status = status
            broker_status.message = message
            broker_status.last_updated = datetime.now()
            broker_status.is_ready = (status == 'success')

            if total_symbols is not None:
                broker_status.total_symbols = str(total_symbols)
            db.add(broker_status)
        else:
            broker_status = MasterContractStatus(
                broker=broker,
                status=status,
                message=message,
                last_updated=datetime.now(),
                is_ready=(status == 'success'),
                total_symbols=str(total_symbols) if total_symbols else '0'
            )
            db.add(broker_status)

        db.commit()
        logger.info(f"Updated master contract status for {broker}: {status}")

    except Exception as e:
        logger.error(f"Error updating status for {broker}: {str(e)}")
        db.rollback()

def get_status(db: Session, broker: str) -> dict:
    """Get the current status for a broker"""
    try:
        status = db.get(MasterContractStatus, broker)

        if status:
            return {
                'broker': status.broker,
                'status': status.status,
                'message': status.message,
                'last_updated': status.last_updated.isoformat() if status.last_updated else None,
                'total_symbols': status.total_symbols,
                'is_ready': status.is_ready
            }
        else:
            return {
                'broker': broker,
                'status': 'unknown',
                'message': 'No status available',
                'last_updated': None,
                'total_symbols': '0',
                'is_ready': False
            }
    except Exception as e:
        logger.error(f"Error getting status for {broker}: {str(e)}")
        return {
            'broker': broker,
            'status': 'error',
            'message': f'Error retrieving status: {str(e)}',
            'last_updated': None,
            'total_symbols': '0',
            'is_ready': False
        }

def check_if_ready(db: Session, broker: str) -> bool:
    """Check if master contracts are ready for a broker"""
    try:
        status = db.get(MasterContractStatus, broker)
        return status.is_ready if status else False
    except Exception as e:
        logger.error(f"Error checking if ready for {broker}: {str(e)}")
        return False
