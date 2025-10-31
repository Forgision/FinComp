# database/apilog_db.py

import json
from datetime import datetime

import pytz
from sqlmodel import Field, Session, SQLModel, create_engine
from app.core.config import settings

from app.utils.logging import logger

LOGS_DATABASE_URL = settings.LOGS_DATABASE_URL
logs_engine = create_engine(LOGS_DATABASE_URL, connect_args={"check_same_thread": False})


class OrderLog(SQLModel, table=True):
    __tablename__ = 'order_logs'
    id: int = Field(default=None, primary_key=True)
    api_type: str
    request_data: str
    response_data: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


def init_db():
    logger.info("Initializing API Log DB")
    SQLModel.metadata.create_all(logs_engine)


async def async_log_order(db: Session, api_type, request_data, response_data):
    try:
        # Serialize JSON data for storage
        request_json = json.dumps(request_data)
        response_json = json.dumps(response_data)

        # Get current time in IST
        ist = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist)

        order_log = OrderLog(api_type=api_type, request_data=request_json,
                             response_data=response_json, created_at=now_ist)
        db.add(order_log)
        db.commit()
    except Exception as e:
        logger.error(f"Error saving order log: {e}")
    finally:
        db.close()
