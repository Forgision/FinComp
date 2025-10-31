# database/tv_search.py

from sqlmodel import Session, select
from app.core.models.symbol import SymToken


def search_symbols(db: Session, symbol: str, exchange: str):
    """
    Searches for symbols matching the given symbol and exchange.

    Args:
        db: The database session.
        symbol: The symbol to search for.
        exchange: The exchange to search in.

    Returns:
        A list of matching SymToken objects.
    """
    statement = select(SymToken).where(SymToken.symbol == symbol, SymToken.exchange == exchange)
    return db.exec(statement).all()
