# app/db/session.py
from typing import Generator
from sqlmodel import create_engine, Session
from app.core.config import settings

# Get database URL from settings
DATABASE_URL = settings.DATABASE_URL

# Conditionally create engine based on DB type
if DATABASE_URL and 'sqlite' in DATABASE_URL:
    # SQLite: Use NullPool to prevent connection pool exhaustion
    # NullPool creates a new connection for each request and closes it when done
    engine = create_engine(
        DATABASE_URL,
        connect_args={'check_same_thread': False}
    )
else:
    # For other databases like PostgreSQL, use connection pooling
    engine = create_engine(
        DATABASE_URL,
        pool_size=50,
        max_overflow=100,
        pool_timeout=10
    )

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI Dependency to create and manage a database session.
    This provides a new, isolated session for each request.
    """
    with Session(engine) as session:
        yield session
