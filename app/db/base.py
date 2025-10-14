# app/db/base.py
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool
from app.core.config import settings

# Get database URL from settings
DATABASE_URL = settings.DATABASE_URL

# Conditionally create engine based on DB type
if DATABASE_URL and 'sqlite' in DATABASE_URL:
    # SQLite: Use NullPool to prevent connection pool exhaustion
    # NullPool creates a new connection for each request and closes it when done
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
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

db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()