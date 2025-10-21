# database/tv_search.py

from app.core.schemas.symbol import SymToken


def search_symbols(symbol,exchange):
    return SymToken.query.filter(SymToken.symbol == symbol,SymToken.exchange == exchange).all()
