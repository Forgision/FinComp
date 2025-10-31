import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

import pytz
from sqlalchemy.orm import Session
from sqlmodel import func, select

from app.utils.logging import logger
from app.core.models.symbol import SymToken
from app.core.config import settings


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    db_queries: int = 0
    bulk_queries: int = 0
    cache_loads: int = 0
    last_loaded: Optional[datetime] = None
    total_symbols: int = 0
    memory_usage_mb: float = 0.0

    def get_hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{self.get_hit_rate():.2f}%",
            'db_queries': self.db_queries,
            'bulk_queries': self.bulk_queries,
            'cache_loads': self.cache_loads,
            'last_loaded': self.last_loaded.isoformat() if self.last_loaded else None,
            'total_symbols': self.total_symbols,
            'memory_usage_mb': f"{self.memory_usage_mb:.2f}"
        }


@dataclass
class SymbolData:
    symbol: str
    brsymbol: str
    name: str
    exchange: str
    brexchange: str
    token: str
    expiry: Optional[str] = None
    strike: Optional[float] = None
    lotsize: Optional[int] = None
    instrumenttype: Optional[str] = None
    tick_size: Optional[float] = None


class BrokerSymbolCache:
    def __init__(self, db: Session):
        self.db = db
        self.active_broker: Optional[str] = None
        self.cache_loaded: bool = False
        self.symbols: Dict[str, SymbolData] = {}
        self.by_symbol_exchange: Dict[Tuple[str, str], SymbolData] = {}
        self.by_token_exchange: Dict[Tuple[str, str], SymbolData] = {}
        self.by_brsymbol_exchange: Dict[Tuple[str, str], SymbolData] = {}
        self.by_token: Dict[str, SymbolData] = {}
        self.stats: CacheStats = CacheStats()
        self.session_start: Optional[datetime] = None
        self.next_reset_time: Optional[datetime] = None
        logger.info("BrokerSymbolCache initialized")

    def load_all_symbols(self, broker: str) -> bool:
        try:
            start_time = time.time()
            logger.info(f"Loading all symbols for broker: {broker}")
            self.clear_cache()
            symbols = self.db.exec(select(SymToken)).all()
            if not symbols:
                logger.warning(f"No symbols found in database for broker: {broker}")
                return False
            for sym in symbols:
                symbol_data = SymbolData(symbol=sym.symbol, brsymbol=sym.brsymbol, name=sym.name, exchange=sym.exchange, brexchange=sym.brexchange, token=sym.token, expiry=sym.expiry, strike=sym.strike, lotsize=sym.lotsize, instrumenttype=sym.instrumenttype, tick_size=sym.tick_size)
                self.symbols[sym.token] = symbol_data
                self.by_symbol_exchange[(sym.symbol, sym.exchange)] = symbol_data
                self.by_token_exchange[(sym.token, sym.exchange)] = symbol_data
                self.by_brsymbol_exchange[(sym.brsymbol, sym.exchange)] = symbol_data
                self.by_token[sym.token] = symbol_data
            self.active_broker = broker
            self.cache_loaded = True
            self.stats.total_symbols = len(symbols)
            self.stats.cache_loads += 1
            self.stats.last_loaded = datetime.now(pytz.timezone('Asia/Kolkata'))
            self.stats.memory_usage_mb = (len(self.symbols) * 500) / (1024 * 1024)
            load_time = time.time() - start_time
            logger.info(f"Successfully loaded {self.stats.total_symbols} symbols in {load_time:.2f} seconds. Memory usage: {self.stats.memory_usage_mb:.2f} MB")
            self._set_session_timing()
            return True
        except Exception as e:
            logger.error(f"Error loading symbols into cache: {e}")
            return False

    def _set_session_timing(self):
        now_ist = datetime.now(pytz.timezone('Asia/Kolkata'))
        self.session_start = now_ist
        expiry_time = settings.SESSION_EXPIRY_TIME
        try:
            hour, minute = map(int, expiry_time.split(':'))
        except ValueError:
            logger.warning(f"Invalid SESSION_EXPIRY_TIME format: {expiry_time}. Using default 03:00")
            hour, minute = 3, 0
        next_reset = now_ist.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now_ist >= next_reset:
            next_reset += timedelta(days=1)
        self.next_reset_time = next_reset
        logger.info(f"Cache valid until: {self.next_reset_time} (Session expiry: {expiry_time})")

    def is_cache_valid(self) -> bool:
        if not self.cache_loaded or not self.next_reset_time:
            return False
        now_ist = datetime.now(pytz.timezone('Asia/Kolkata'))
        return now_ist < self.next_reset_time

    def get_token(self, symbol: str, exchange: str) -> Optional[str]:
        self.stats.hits += 1
        data = self.by_symbol_exchange.get((symbol, exchange))
        if data:
            return data.token
        self.stats.hits -= 1
        self.stats.misses += 1
        return None

    def get_symbol(self, token: str, exchange: str) -> Optional[str]:
        self.stats.hits += 1
        data = self.by_token_exchange.get((token, exchange))
        if data:
            return data.symbol
        self.stats.hits -= 1
        self.stats.misses += 1
        return None

    def get_br_symbol(self, symbol: str, exchange: str) -> Optional[str]:
        self.stats.hits += 1
        data = self.by_symbol_exchange.get((symbol, exchange))
        if data:
            return data.brsymbol
        self.stats.hits -= 1
        self.stats.misses += 1
        return None

    def get_oa_symbol(self, brsymbol: str, exchange: str) -> Optional[str]:
        self.stats.hits += 1
        data = self.by_brsymbol_exchange.get((brsymbol, exchange))
        if data:
            return data.symbol
        self.stats.hits -= 1
        self.stats.misses += 1
        return None

    def get_brexchange(self, symbol: str, exchange: str) -> Optional[str]:
        self.stats.hits += 1
        data = self.by_symbol_exchange.get((symbol, exchange))
        if data:
            return data.brexchange
        self.stats.hits -= 1
        self.stats.misses += 1
        return None

    def get_symbol_data(self, token: str) -> Optional[SymbolData]:
        self.stats.hits += 1
        data = self.by_token.get(token)
        if data:
            return data
        self.stats.hits -= 1
        self.stats.misses += 1
        return None

    def get_tokens_bulk(self, symbol_exchange_pairs: List[Tuple[str, str]]) -> List[Optional[str]]:
        self.stats.bulk_queries += 1
        results = []
        for symbol, exchange in symbol_exchange_pairs:
            data = self.by_symbol_exchange.get((symbol, exchange))
            if data:
                results.append(data.token)
                self.stats.hits += 1
            else:
                results.append(None)
                self.stats.misses += 1
        return results

    def get_symbols_bulk(self, token_exchange_pairs: List[Tuple[str, str]]) -> List[Optional[str]]:
        self.stats.bulk_queries += 1
        results = []
        for token, exchange in token_exchange_pairs:
            data = self.by_token_exchange.get((token, exchange))
            if data:
                results.append(data.symbol)
                self.stats.hits += 1
            else:
                results.append(None)
                self.stats.misses += 1
        return results

    def search_symbols(self, query: str, exchange: Optional[str] = None, limit: int = 50) -> List[SymbolData]:
        query_upper = query.upper()
        matches = []
        for symbol_data in self.symbols.values():
            if exchange and symbol_data.exchange != exchange:
                continue
            if (query_upper in symbol_data.symbol.upper() or query_upper in symbol_data.brsymbol.upper() or (symbol_data.name and query_upper in symbol_data.name.upper())):
                matches.append(symbol_data)
                if len(matches) >= limit:
                    break
        return matches

    def clear_cache(self):
        self.symbols.clear()
        self.by_symbol_exchange.clear()
        self.by_token_exchange.clear()
        self.by_brsymbol_exchange.clear()
        self.by_token.clear()
        self.cache_loaded = False
        self.active_broker = None
        logger.info("Cache cleared")

    def get_cache_info(self) -> Dict[str, Any]:
        return {'active_broker': self.active_broker, 'cache_loaded': self.cache_loaded, 'total_symbols': self.stats.total_symbols, 'cache_valid': self.is_cache_valid(), 'session_start': self.session_start.isoformat() if self.session_start else None, 'next_reset': self.next_reset_time.isoformat() if self.next_reset_time else None, 'stats': self.stats.to_dict()}


_cache_instance: Optional[BrokerSymbolCache] = None


def get_cache(db: Session) -> BrokerSymbolCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = BrokerSymbolCache(db)
    return _cache_instance


def get_token(db: Session, symbol: str, exchange: str) -> Optional[str]:
    cache = get_cache(db)
    if cache.cache_loaded and cache.is_cache_valid():
        result = cache.get_token(symbol, exchange)
        if result is not None:
            return result
    cache.stats.db_queries += 1
    return get_token_dbquery(db, symbol, exchange)


def get_symbol(db: Session, token: str, exchange: str) -> Optional[str]:
    cache = get_cache(db)
    if cache.cache_loaded and cache.is_cache_valid():
        result = cache.get_symbol(token, exchange)
        if result is not None:
            return result
    cache.stats.db_queries += 1
    return get_symbol_dbquery(db, token, exchange)


def get_br_symbol(db: Session, symbol: str, exchange: str) -> Optional[str]:
    cache = get_cache(db)
    if cache.cache_loaded and cache.is_cache_valid():
        result = cache.get_br_symbol(symbol, exchange)
        if result is not None:
            return result
    cache.stats.db_queries += 1
    return get_br_symbol_dbquery(db, symbol, exchange)


def get_oa_symbol(db: Session, brsymbol: str, exchange: str) -> Optional[str]:
    cache = get_cache(db)
    if cache.cache_loaded and cache.is_cache_valid():
        result = cache.get_oa_symbol(brsymbol, exchange)
        if result is not None:
            return result
    cache.stats.db_queries += 1
    return get_oa_symbol_dbquery(db, brsymbol, exchange)


def get_brexchange(db: Session, symbol: str, exchange: str) -> Optional[str]:
    cache = get_cache(db)
    if cache.cache_loaded and cache.is_cache_valid():
        result = cache.get_brexchange(symbol, exchange)
        if result is not None:
            return result
    cache.stats.db_queries += 1
    return get_brexchange_dbquery(db, symbol, exchange)


def get_token_dbquery(db: Session, symbol: str, exchange: str) -> Optional[str]:
    try:
        sym_token = db.exec(select(SymToken).where(SymToken.symbol == symbol, SymToken.exchange == exchange)).first()
        return sym_token.token if sym_token else None
    except Exception as e:
        logger.error(f"Error while querying the database: {e}")
        return None


def get_symbol_dbquery(db: Session, token: str, exchange: str) -> Optional[str]:
    try:
        sym_token = db.exec(select(SymToken).where(SymToken.token == token, SymToken.exchange == exchange)).first()
        return sym_token.symbol if sym_token else None
    except Exception as e:
        logger.error(f"Error while querying the database: {e}")
        return None


def get_br_symbol_dbquery(db: Session, symbol: str, exchange: str) -> Optional[str]:
    try:
        sym_token = db.exec(select(SymToken).where(SymToken.symbol == symbol, SymToken.exchange == exchange)).first()
        return sym_token.brsymbol if sym_token else None
    except Exception as e:
        logger.error(f"Error while querying the database: {e}")
        return None


def get_oa_symbol_dbquery(db: Session, brsymbol: str, exchange: str) -> Optional[str]:
    try:
        sym_token = db.exec(select(SymToken).where(SymToken.brsymbol == brsymbol, SymToken.exchange == exchange)).first()
        return sym_token.symbol if sym_token else None
    except Exception as e:
        logger.error(f"Error while querying the database: {e}")
        return None


def get_brexchange_dbquery(db: Session, symbol: str, exchange: str) -> Optional[str]:
    try:
        sym_token = db.exec(select(SymToken).where(SymToken.symbol == symbol, SymToken.exchange == exchange)).first()
        return sym_token.brexchange if sym_token else None
    except Exception as e:
        logger.error(f"Error while querying the database: {e}")
        return None


def get_symbol_count(db: Session) -> int:
    try:
        count = db.scalar(select(func.count(SymToken.id)))
        return count
    except Exception as e:
        logger.error(f"Error while counting symbols: {e}")
        return 0


def load_cache_for_broker(db: Session, broker: str) -> bool:
    cache = get_cache(db)
    return cache.load_all_symbols(broker)


def clear_cache(db: Session):
    cache = get_cache(db)
    cache.clear_cache()


def get_cache_stats(db: Session) -> Dict[str, Any]:
    cache = get_cache(db)
    return cache.get_cache_info()


def get_tokens_bulk(db: Session, symbol_exchange_pairs: List[Tuple[str, str]]) -> List[Optional[str]]:
    cache = get_cache(db)
    if cache.cache_loaded and cache.is_cache_valid():
        return cache.get_tokens_bulk(symbol_exchange_pairs)
    results = []
    for symbol, exchange in symbol_exchange_pairs:
        cache.stats.db_queries += 1
        results.append(get_token_dbquery(db, symbol, exchange))
    return results


def get_symbols_bulk(db: Session, token_exchange_pairs: List[Tuple[str, str]]) -> List[Optional[str]]:
    cache = get_cache(db)
    if cache.cache_loaded and cache.is_cache_valid():
        return cache.get_symbols_bulk(token_exchange_pairs)
    results = []
    for token, exchange in token_exchange_pairs:
        cache.stats.db_queries += 1
        results.append(get_symbol_dbquery(db, token, exchange))
    return results


def search_symbols(db: Session, query: str, exchange: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    cache = get_cache(db)
    if cache.cache_loaded and cache.is_cache_valid():
        results = cache.search_symbols(query, exchange, limit)
        return [{'symbol': s.symbol, 'brsymbol': s.brsymbol, 'name': s.name, 'exchange': s.exchange, 'token': s.token, 'instrumenttype': s.instrumenttype} for s in results]
    try:
        statement = select(SymToken).where(SymToken.symbol.like(f'%{query}%'))
        if exchange:
            statement = statement.where(SymToken.exchange == exchange)
        results = db.exec(statement.limit(limit)).all()
        return [{'symbol': r.symbol, 'brsymbol': r.brsymbol, 'name': r.name, 'exchange': r.exchange, 'token': r.token, 'instrumenttype': r.instrumenttype} for r in results]
    except Exception as e:
        logger.error(f"Error searching symbols: {e}")
        return []
