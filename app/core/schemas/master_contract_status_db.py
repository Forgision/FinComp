import logging
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, select
from sqlalchemy.orm import Mapped, mapped_column

from . import engine, Base, AsyncSessionLocal as AsyncSessionLocal

logger = logging.getLogger(__name__)

class MasterContractStatus(Base):
    __tablename__ = 'master_contract_status'

    broker: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default='pending')
    message: Mapped[str] = mapped_column(String)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    total_symbols: Mapped[str] = mapped_column(String, default='0')
    is_ready: Mapped[bool] = mapped_column(Boolean, default=False)

# Create table if it doesn't exist
def init_db():
    """Initialize the database"""
    Base.metadata.create_all(bind=engine)

def init_broker_status(broker):
    """Initialize status for a broker when they login"""
    session = AsyncSessionLocal()
    try:
        # Check if status already exists
        stmt = select(MasterContractStatus).filter_by(broker=broker)
        existing = session.execute(stmt).scalars().first()

        if existing:
            # Update existing status
            existing.status = 'pending'
            existing.message = 'Master contract download pending'
            existing.last_updated = datetime.now()
            existing.is_ready = False
        else:
            # Create new status
            status = MasterContractStatus(
                broker=broker,
                status='pending',
                message='Master contract download pending',
                last_updated=datetime.now(),
                is_ready=False
            )
            session.add(status)

        session.commit()
        logger.info(f"Initialized master contract status for {broker}")

    except Exception as e:
        logger.error(f"Error initializing status for {broker}: {str(e)}")
        session.rollback()
    finally:
        session.close()

def update_status(broker, status, message, total_symbols=None):
    """Update the download status for a broker"""
    session = AsyncSessionLocal()
    try:
        stmt = select(MasterContractStatus).filter_by(broker=broker)
        broker_status = session.execute(stmt).scalars().first()

        if broker_status:
            broker_status.status = status
            broker_status.message = message
            broker_status.last_updated = datetime.now()
            broker_status.is_ready = (status == 'success')

            if total_symbols is not None:
                broker_status.total_symbols = str(total_symbols)
        else:
            # Create new status if it doesn't exist
            broker_status = MasterContractStatus(
                broker=broker,
                status=status,
                message=message,
                last_updated=datetime.now(),
                is_ready=(status == 'success'),
                total_symbols=str(total_symbols) if total_symbols else '0'
            )
            session.add(broker_status)

        session.commit()
        logger.info(f"Updated master contract status for {broker}: {status}")

    except Exception as e:
        logger.error(f"Error updating status for {broker}: {str(e)}")
        session.rollback()
    finally:
        session.close()

def get_status(broker):
    """Get the current status for a broker"""
    session = AsyncSessionLocal()
    try:
        stmt = select(MasterContractStatus).filter_by(broker=broker)
        status = session.execute(stmt).scalars().first()

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
    finally:
        session.close()

def check_if_ready(broker):
    """Check if master contracts are ready for a broker"""
    session = AsyncSessionLocal()
    try:
        stmt = select(MasterContractStatus).filter_by(broker=broker)
        status = session.execute(stmt).scalars().first()
        return status.is_ready if status else False
    except Exception as e:
        logger.error(f"Error checking if ready for {broker}: {str(e)}")
        return False
    finally:
        session.close()
