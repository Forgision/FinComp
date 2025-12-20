from app.core.services.holdings_service import import_broker_module as import_broker_holdings
from app.core.services.positionbook_service import import_broker_module as import_broker_positions
from app.core.services.orderbook_service import import_broker_module as import_broker_orders
from app.core.services.tradebook_service import import_broker_module as import_broker_trades

def test_holdings_import_cache():
    # clear cache first
    import_broker_holdings.cache_clear()

    # First call - should be a miss
    import_broker_holdings("dummy_broker")
    info = import_broker_holdings.cache_info()
    assert info.hits == 0
    assert info.misses == 1

    # Second call - should be a hit
    import_broker_holdings("dummy_broker")
    info = import_broker_holdings.cache_info()
    assert info.hits == 1
    assert info.misses == 1

def test_positions_import_cache():
    import_broker_positions.cache_clear()
    import_broker_positions("dummy_broker")
    assert import_broker_positions.cache_info().misses == 1
    import_broker_positions("dummy_broker")
    assert import_broker_positions.cache_info().hits == 1

def test_orders_import_cache():
    import_broker_orders.cache_clear()
    import_broker_orders("dummy_broker")
    assert import_broker_orders.cache_info().misses == 1
    import_broker_orders("dummy_broker")
    assert import_broker_orders.cache_info().hits == 1

def test_trades_import_cache():
    import_broker_trades.cache_clear()
    import_broker_trades("dummy_broker")
    assert import_broker_trades.cache_info().misses == 1
    import_broker_trades("dummy_broker")
    assert import_broker_trades.cache_info().hits == 1
