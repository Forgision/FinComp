from typing import List

from sqlalchemy import (
    Float,
    Index,
    Integer,
    Sequence,
    String,
    and_,
    create_engine,
    or_,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, scoped_session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.utils.logging import logger

DATABASE_URL = settings.DATABASE_URL
# Conditionally create engine based on DB type
if DATABASE_URL and 'sqlite' in DATABASE_URL:
    # SQLite: Use NullPool to prevent connection pool exhaustion
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

class Base(DeclarativeBase):
    pass

class SymToken(Base):
    __tablename__ = 'symtoken'
    id: Mapped[int] = mapped_column(Integer, Sequence('symtoken_id_seq'), primary_key=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    brsymbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String)
    exchange: Mapped[str] = mapped_column(String, index=True)
    brexchange: Mapped[str] = mapped_column(String, index=True)
    token: Mapped[str] = mapped_column(String, index=True)
    expiry: Mapped[str] = mapped_column(String)
    strike: Mapped[float] = mapped_column(Float)
    lotsize: Mapped[int] = mapped_column(Integer)
    instrumenttype: Mapped[str] = mapped_column(String)
    tick_size: Mapped[float] = mapped_column(Float)

    # Composite indices for improved search performance
    __table_args__ = (
        Index('idx_symbol_exchange', 'symbol', 'exchange'),
        Index('idx_symbol_name', 'symbol', 'name'),
        Index('idx_brsymbol_exchange', 'brsymbol', 'exchange'),
    )

def enhanced_search_symbols(query: str, exchange: str = None) -> List[SymToken]:
    """
    Enhanced search function that searches across multiple fields
    and supports partial matching with multiple terms

    Args:
        query (str): Search query string
        exchange (str, optional): Exchange to filter by

    Returns:
        List[SymToken]: List of matching SymToken objects
    """
    try:
        # Split the query into terms and clean them
        terms = [term.strip().upper() for term in query.split() if term.strip()]

        # Base query
        stmt = select(SymToken)

        # If exchange is specified, filter by it
        if exchange:
            stmt = stmt.filter(SymToken.exchange == exchange)

        # Create conditions for each term
        all_conditions = []
        for term in terms:
            # Number detection for more accurate strike price and token searches
            try:
                num_term = float(term)
                term_conditions = or_(
                    SymToken.symbol.ilike(f'%{term}%'),
                    SymToken.brsymbol.ilike(f'%{term}%'),
                    SymToken.name.ilike(f'%{term}%'),
                    SymToken.token.ilike(f'%{term}%'),
                    SymToken.strike == num_term
                )
            except ValueError:
                term_conditions = or_(
                    SymToken.symbol.ilike(f'%{term}%'),
                    SymToken.brsymbol.ilike(f'%{term}%'),
                    SymToken.name.ilike(f'%{term}%'),
                    SymToken.token.ilike(f'%{term}%')
                )
            all_conditions.append(term_conditions)

        # Combine all conditions with AND
        if all_conditions:
            stmt = stmt.filter(and_(*all_conditions))

        # Execute query - no limit to show all matching results
        results = db_session.execute(stmt).scalars().all()
        return results

    except Exception as e:
        logger.error(f"Error in enhanced search: {str(e)}")
        return []

def init_db():
    """Initialize the database"""
    logger.info("Initializing Master Contract DB")
    Base.metadata.create_all(bind=engine)
