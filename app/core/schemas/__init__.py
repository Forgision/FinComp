# This module contains all DataBase Model

# app/db/base.py
from typing import (
    AsyncGenerator,
    Callable,
    Coroutine,
    Any,
    NamedTuple,
    TypeAlias,
    Union,
)
from dataclasses import dataclass

from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
    AsyncSession,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.utils.logging import logger
import inspect


@dataclass(frozen=True)
class DBConnectionConfig:
    """
    Configuration for database connection.
    """

    database_url: str
    echo: bool = False
    pool_size: int = 50
    max_overflow: int = 100
    pool_timeout: int = 10


class DatabaseConnectionError(Exception):
    """Custom exception for database connection errors."""

    pass


# Dependency to get the database session
DBDependency: TypeAlias = Callable[[], AsyncGenerator[AsyncSession, None]]


class DBConnectionTuple(NamedTuple):
    engine: AsyncEngine
    session_maker: async_sessionmaker[AsyncSession]
    get_db_dependency: DBDependency


def make_db_connection(
    config: DBConnectionConfig,
) -> DBConnectionTuple:
    """
    Create an asynchronous SQLAlchemy engine and session factory and return:
        (engine, AsyncSessionLocal, dependency_get_db)

    Args:
        config: Configuration object for the database connection.

    Returns:
        DBConnectionTuple: A named tuple containing the AsyncEngine,
                           async_sessionmaker, and the dependency function.
    """
    if not config.database_url:
        raise ValueError("database_url must be provided in DBConnectionConfig")

    # Sanitize database URL for logging (remove credentials)
    log_database_url = (
        config.database_url.split("@")[-1]
        if "@" in config.database_url
        else config.database_url
    )
    log_database_url = (
        f"***:***@{log_database_url.split('://', 1)[1]}"
        if "://" in log_database_url
        else log_database_url
    )

    # SQLite (aiosqlite) should not use a connection pool and needs 'check_same_thread'
    is_sqlite = "sqlite" in config.database_url.lower()

    engine_args: dict[str, Any] = {
        "echo": config.echo,
    }

    if is_sqlite:
        logger.info(f"Creating async SQLite engine (NullPool) for {log_database_url}.")
        engine_args.update(
            {
                "connect_args": {"check_same_thread": False},
                "poolclass": NullPool,
            }
        )
    else:
        logger.info(f"Creating async engine with pooling for {log_database_url}.")
        engine_args.update(
            {
                "pool_size": config.pool_size,
                "max_overflow": config.max_overflow,
                "pool_timeout": config.pool_timeout,
            }
        )

    try:
        engine = create_async_engine(
            config.database_url,
            **engine_args,
        )
    except SQLAlchemyError as e:
        logger.error(f"Failed to create SQLAlchemy engine for {log_database_url}: {e}")
        raise DatabaseConnectionError(f"Could not connect to database: {e}") from e

    # Use AsyncSession class, avoid expiring on commit by default (common pattern)
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        """Dependency that yields a DB session; use in FastAPI dependencies."""
        logger.debug("Acquiring database session.")
        try:
            async with AsyncSessionLocal() as session:
                yield session
        except SQLAlchemyError as e:
            logger.error(f"Database session error: {e}")
            raise
        finally:
            logger.debug("Database session released.")

    return DBConnectionTuple(engine, AsyncSessionLocal, get_db)


class Base(DeclarativeBase):
    pass


db_config = DBConnectionConfig(
    database_url=settings.DATABASE_URL,
    echo=False,  # You might want to get this from settings too
    pool_size=50,  # And these
    max_overflow=100,
    pool_timeout=10,
)
engine, AsyncSessionLocal, get_db = make_db_connection(db_config)


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
