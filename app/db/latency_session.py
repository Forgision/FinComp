import logging
import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from app.core.config import settings

logger = logging.getLogger(__name__)

# Use a separate database for latency logs
LATENCY_DATABASE_URL = settings.LATENCY_DATABASE_URL

# Conditionally create engine based on DB type
if LATENCY_DATABASE_URL and 'sqlite' in LATENCY_DATABASE_URL:
    # SQLite: Use NullPool to prevent connection pool exhaustion
    latency_engine = create_engine(
        LATENCY_DATABASE_URL,
        poolclass=NullPool,
        connect_args={'check_same_thread': False}
    )
else:
    # For other databases like PostgreSQL, use connection pooling
    latency_engine = create_engine(
        LATENCY_DATABASE_URL,
        pool_size=50,
        max_overflow=100,
        pool_timeout=10
    )

LatencySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=latency_engine)

def get_latency_db() -> Generator[Session, None, None]:
    """
    Dependency to get a database session for the latency database.
    """
    db = LatencySessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_latency_db():
    """
    Initialize the latency database: create the necessary directory and tables.
    """
    if 'sqlite' in LATENCY_DATABASE_URL:
        # Extract directory from app.core.schemas URL and create if it doesn't exist
        db_path = LATENCY_DATABASE_URL.replace('sqlite:///', '')
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Ensured directory exists for latency DB: {db_dir}")

    logger.info(f"Initializing Latency DB at: {LATENCY_DATABASE_URL}")
    # Import all models related to the latency DB here before creating tables
    # This is currently empty but is a placeholder for when models are moved
    # from app.core.models import latency_db
    SQLModel.metadata.create_all(bind=latency_engine)
    logger.info("Latency DB initialized.")
