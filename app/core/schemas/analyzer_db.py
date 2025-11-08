# database/analyzer_db.py

import json
from datetime import datetime

import pytz
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import Base
from app.utils.logging import logger
from app.core.config import settings


class AnalyzerLog(Base):
    __tablename__ = 'analyzer_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # placeorder, cancelorder, etc.
    api_type: Mapped[str] = mapped_column(String(50), nullable=False)
    request_data: Mapped[str] = mapped_column(Text, nullable=False)
    response_data: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now())

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


async def async_log_analyzer(db: AsyncSession, request_data, response_data, api_type='placeorder'):
    """Asynchronously log analyzer request"""
    try:
        # Serialize JSON data for storage
        request_json = json.dumps(request_data)
        response_json = json.dumps(response_data)

        # Get current time in IST
        ist = pytz.timezone(settings.TIMEZONE)
        now_ist = datetime.now(ist)

        analyzer_log = AnalyzerLog(
            api_type=api_type,
            request_data=request_json,
            response_data=response_json,
            created_at=now_ist
        )
        db.add(analyzer_log)
        await db.commit()
    except Exception as e:
        logger.error(f"Error saving analyzer log: {e}")
        await db.rollback()
    finally:
        await db.close()
