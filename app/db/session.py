# app/db/session.py
# This file manages the database session using SQLAlchemy for website.

from contextlib import contextmanager
from sqlalchemy import NullPool, create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from app.core.config import settings

# Create the SQLAlchemy engine
engine = create_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        connect_args={'check_same_thread': False}
    )

# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)

# Dependency to get the database session
# @contextmanager
def get_db():
    db = db_session()
    try:
        yield db
    finally:
        db.close()