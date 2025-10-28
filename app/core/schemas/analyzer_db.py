# database/analyzer_db.py

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytz
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.schemas.base import Base
from app.core.schemas.session import engine, get_db
from app.utils.logging import logger


class AnalyzerLog(Base):
    __tablename__ = 'analyzer_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    api_type: Mapped[str] = mapped_column(String(50), nullable=False)  # placeorder, cancelorder, etc.
    request_data: Mapped[str] = mapped_column(Text, nullable=False)
    response_data: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    def to_dict(self):
        """Convert log entry to dictionary"""
        try:
            request_data = json.loads(self.request_data) if isinstance(self.request_data, str) else self.request_data
            response_data = json.loads(self.response_data) if isinstance(self.response_data, str) else self.response_data
        except json.JSONDecodeError:
            request_data = self.request_data
            response_data = self.response_data

        return {
            'id': self.id,
            'api_type': self.api_type,
            'request_data': request_data,
            'response_data': response_data,
            'created_at': self.created_at.astimezone(pytz.UTC).isoformat()
        }

def init_db():
    """Initialize the analyzer table"""
    logger.info("Initializing Analyzer Table")
    Base.metadata.create_all(bind=engine)

# Executor for asynchronous tasks
executor = ThreadPoolExecutor(10)  # Increased from 2 to 10 for better concurrency

def async_log_analyzer(request_data, response_data, api_type='placeorder'):
    """Asynchronously log analyzer request"""
    db = next(get_db())
    try:
        # Serialize JSON data for storage
        request_json = json.dumps(request_data)
        response_json = json.dumps(response_data)

        # Get current time in IST
        ist = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist)

        analyzer_log = AnalyzerLog(
            api_type=api_type,
            request_data=request_json,
            response_data=response_json,
            created_at=now_ist
        )
        db.add(analyzer_log)
        db.commit()
    except Exception as e:
        logger.error(f"Error saving analyzer log: {e}")
        db.rollback()
    finally:
        db.close()
