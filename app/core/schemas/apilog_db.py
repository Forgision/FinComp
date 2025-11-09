# database/apilog_db.py

import json
from datetime import datetime

import pytz
from sqlalchemy import DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import Base
from app.utils.logging import logger


class OrderLog(Base):
    __tablename__ = "order_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    api_type: Mapped[str] = mapped_column(Text, nullable=False)
    request_data: Mapped[str] = mapped_column(Text, nullable=False)
    response_data: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )


async def async_log_order(db: AsyncSession, api_type, request_data, response_data):
    try:
        # Serialize JSON data for storage
        request_json = json.dumps(request_data)
        response_json = json.dumps(response_data)

        # Get current time in IST
        ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(ist)

        order_log = OrderLog(
            api_type=api_type,
            request_data=request_json,
            response_data=response_json,
            created_at=now_ist,
        )
        db.add(order_log)
        await db.commit()
    except Exception as e:
        logger.error(f"Error saving order log: {e}")
    finally:
        await db.close()
