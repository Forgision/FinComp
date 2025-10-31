import logging
import os
from typing import Generator

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlmodel import SQLModel

from app.core.config import settings

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = settings.TELEGRAM_DATABASE_URL

if DATABASE_URL.startswith('sqlite:///') and ':memory:' not in DATABASE_URL:
    # Ensure the directory exists for file-based SQLite, but not for in-memory
    db_path = DATABASE_URL.replace('sqlite:///', '')
    if os.path.dirname(db_path): # Only create if a directory is specified
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

telegram_engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
TelegramSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=telegram_engine)

def get_telegram_db() -> Generator[Session, None, None]:
    """
    Dependency to get a database session for the telegram database.
    """
    db = TelegramSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_telegram_db():
    """Initialize the database with required tables"""
    try:
        from app.core.models.telegram_db import BotConfig
        SQLModel.metadata.create_all(bind=telegram_engine)

        # Create default bot config if not exists
        with TelegramSessionLocal() as session:
            stmt = select(BotConfig).where(BotConfig.id == 1)
            config = session.exec(stmt).first()
            if not config:
                default_config = BotConfig(id=1)
                session.add(default_config)
                session.commit()

        logger.info("Telegram database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize telegram database: {str(e)}")
