from typing import List, Optional

from sqlalchemy import and_, or_, Index
from sqlalchemy.orm import Session
from sqlmodel import Field, SQLModel, select

from app.utils.logging import logger


class SymToken(SQLModel, table=True):
    __tablename__ = 'symtoken'

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    brsymbol: str = Field(index=True)
    name: str
    exchange: str = Field(index=True)
    brexchange: str = Field(index=True)
    token: str = Field(index=True)
    expiry: str
    strike: float
    lotsize: int
    instrumenttype: str
    tick_size: float

    __table_args__ = (
        Index('idx_symbol_exchange', 'symbol', 'exchange'),
        Index('idx_symbol_name', 'symbol', 'name'),
        Index('idx_brsymbol_exchange', 'brsymbol', 'exchange'),
        {'extend_existing': True}
    )


def enhanced_search_symbols(db: Session, query: str, exchange: Optional[str] = None) -> List[SymToken]:
    """
    Enhanced search function that searches across multiple fields
    and supports partial matching with multiple terms

    Args:
        db (Session): The database session.
        query (str): Search query string
        exchange (str, optional): Exchange to filter by

    Returns:
        List[SymToken]: List of matching SymToken objects
    """
    try:
        terms = [term.strip().upper() for term in query.split() if term.strip()]
        statement = select(SymToken)

        if exchange:
            statement = statement.where(SymToken.exchange == exchange)

        all_conditions = []
        for term in terms:
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

        if all_conditions:
            statement = statement.where(and_(*all_conditions))

        results = db.exec(statement).all()
        return list(results)

    except Exception as e:
        logger.error(f"Error in enhanced search: {str(e)}")
        return []
