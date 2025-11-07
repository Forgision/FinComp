# This module contains all DataBase Model

# app/db/base.py
from typing import AsyncGenerator, Callable, Union, Coroutine, Any
# from functools import partial

from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncEngine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.utils.logging import logger
import inspect


# Dependency to get the database session
async def make_get_db(session_local: async_sessionmaker):
    async with session_local() as session:
        yield session


def make_db_connection(
    database_url: str,
) -> tuple[AsyncEngine, async_sessionmaker, AsyncGenerator[async_sessionmaker, None]]:
    
    # Conditionally create engine based on DB type
    if database_url and "sqlite" in database_url:
        # Asynchronous engine for SQLite
        engine = create_async_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=NullPool,
        )
    else:
        # For other databases like PostgreSQL, use connection pooling
        engine = create_async_engine(
            database_url,
            pool_size=50,
            max_overflow=100,
            pool_timeout=10,
        )

    # Create a SessionLocal class
    AsyncSessionLocal = async_sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    
    async def make_get_db():
        async with AsyncSessionLocal() as session:
            yield session
    
    # return engine, AsyncSessionLocal, partial(make_get_db, AsyncSessionLocal)
    return engine, AsyncSessionLocal, make_get_db


class Base(DeclarativeBase):
    pass


engine, AsyncSessionLocal, get_db = make_db_connection(settings.DATABASE_URL)


INIT_DB_REGISTRY: dict[
    str, Union[Callable, Callable[..., Coroutine[Any, Any, Any]]]
] = {}


async def initizing_databases():
    logger.info("Initializing All Databases")
    
    logger.debug("Initializing opendb")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.debug("Initializing opendb done")

    for name, func in INIT_DB_REGISTRY.items():
        logger.debug(f"Initializing {name}")
        # Check func is async

        if inspect.iscoroutinefunction(func):
            await func()
        else:
            func()
        logger.debug(f"Initialized {name}")

    logger.info("Initialized All Databases Done")
