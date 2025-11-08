# database/tv_search.py

from sqlalchemy import select
from app.core.schemas.symbol import SymToken
from app.core.schemas import AsyncSessionLocal


async def search_symbols(symbol: str, exchange: str):
    """
    Searches for symbols matching the given symbol and exchange.

    Args:
        symbol: The symbol to search for.
        exchange: The exchange to search in.

    Returns:
        A list of matching SymToken objects.
    """

    async with AsyncSessionLocal() as db_session:
        stmt = select(SymToken).filter(
            SymToken.symbol == symbol, SymToken.exchange == exchange
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()
