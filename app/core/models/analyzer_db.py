# database/analyzer_db.py

import json
from datetime import datetime

import pytz
from sqlmodel import Field, Session, SQLModel, create_engine
from app.core.config import settings

from app.utils.logging import logger

LOGS_DATABASE_URL = settings.LOGS_DATABASE_URL
logs_engine = create_engine(LOGS_DATABASE_URL, connect_args={"check_same_thread": False})


class AnalyzerLog(SQLModel, table=True):
    __tablename__ = 'analyzer_logs'
    id: int = Field(default=None, primary_key=True)
    # placeorder, cancelorder, etc.
    api_type: str = Field(max_length=50)
    request_data: str
    response_data: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_dict(self):
        """Convert log entry to dictionary"""
        try:
            request_data = json.loads(
                self.request_data) if isinstance(self.request_data, str) else self.request_data
            response_data = json.loads(
                self.response_data) if isinstance(self.response_data, str) else self.response_data
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
    SQLModel.metadata.create_all(logs_engine)

# Executor for asynchronous tasks


async def async_log_analyzer(db: Session, request_data, response_data, api_type='placeorder'):
    """Asynchronously log analyzer request"""
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
