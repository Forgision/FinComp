## 2024-05-22 - Async Sequential Await in Analyze Mode
**Learning:** Found sequential `await` calls inside a loop for `sandbox_place_order` in `basket_order_service.py`. This caused linear latency growth with the number of orders in a basket.
**Action:** Refactored to use `asyncio.gather()` for concurrent execution.
**Crucial Details:**
1. **Ordering:** Must maintain "BUYs then SELLs" execution order. Split into two `asyncio.gather` phases (Batch BUYs, await, then Batch SELLs).
2. **Concurrency Safety:** Each concurrent task must instantiate its own `AsyncSession` using `AsyncSessionLocal()` because SQLAlchemy sessions are not concurrency-safe.
3. **Resource Management:** Use `asyncio.Semaphore` to limit concurrent DB connections and avoid pool exhaustion.

## 2025-12-19 - Blocking Broker APIs in Basket Order Service
**Learning:** `place_single_order` in `basket_order_service.py` was calling broker APIs directly. Legacy brokers have synchronous APIs, which blocked the asyncio event loop, defeating the purpose of `asyncio.gather`. Newer brokers (Fyers) have async APIs, but the code was not awaiting them, causing runtime crashes.
**Action:** Implemented dynamic detection using `inspect.iscoroutinefunction`. Async functions are awaited; sync functions are offloaded to `loop.run_in_executor` to ensure non-blocking concurrent execution.
**Crucial Details:**
1. **Dynamic Support:** Services must handle both sync and async broker implementations during the migration phase.
2. **Mixed Mode Concurrency:** `asyncio.gather` can manage both native coroutines and `run_in_executor` futures effectively.
