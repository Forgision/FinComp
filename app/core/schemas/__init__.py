# This module contains all DataBase Model

# app/db/base.py
from typing import Callable
from sqlalchemy import NullPool, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
from app.utils.logging import logger



# Conditionally create engine based on DB type
if settings.DATABASE_URL and 'sqlite' in settings.DATABASE_URL:
    # SQLite: Use NullPool to prevent connection pool exhaustion
    # NullPool creates a new connection for each request and closes it when done
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        connect_args={'check_same_thread': False}
    )
else:
    # For other databases like PostgreSQL, use connection pooling
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=50,
        max_overflow=100,
        pool_timeout=10
    )
    

class Base(DeclarativeBase):
    pass


# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get the database session
# @contextmanager
def get_db():# -> Generator[Any, Any, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
ENSURE_TABLE_REGISTRY: dict[str, Callable]= {}


def initizing_databases():
    logger.info("Initializing Database")
    
    Base.metadata.create_all(bind=engine
                             )
    for name, func in ENSURE_TABLE_REGISTRY.items():
        logger.debug(f"Initializing {name}")
        func()
        logger.debug(f"Initialized {name}")
    
    logger.info("Database Initialized")
    

