"""
Token Database Module - Enhanced with Full Memory Cache
This module provides the same API as before but now uses intelligent in-memory caching
for 100,000+ symbols with O(1) lookup performance.

All existing code will continue to work without any changes.
"""

from cachetools import TTLCache

from app.core.models.token_db_enhanced import (
    clear_cache,
    get_br_symbol,
    get_br_symbol_dbquery,
    get_brexchange,
    get_brexchange_dbquery,
    get_cache_stats,
    get_oa_symbol,
    get_oa_symbol_dbquery,
    get_symbol,
    get_symbol_count,
    get_symbol_dbquery,
    get_symbols_bulk,
    get_token,
    get_token_dbquery,
    get_tokens_bulk,
    load_cache_for_broker,
    search_symbols,
)

token_cache = TTLCache(maxsize=1024, ttl=3600)

__all__ = [
    'get_token',
    'get_symbol',
    'get_oa_symbol',
    'get_br_symbol',
    'get_brexchange',
    'get_symbol_count',
    'get_token_dbquery',
    'get_symbol_dbquery',
    'get_oa_symbol_dbquery',
    'get_br_symbol_dbquery',
    'get_brexchange_dbquery',
    'token_cache',
    'get_tokens_bulk',
    'get_symbols_bulk',
    'search_symbols',
    'load_cache_for_broker',
    'clear_cache',
    'get_cache_stats'
]
