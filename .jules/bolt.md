## 2024-05-22 - Async Sequential Await in Analyze Mode
**Learning:** Found sequential `await` calls inside a loop for `sandbox_place_order` in `basket_order_service.py`. This caused linear latency growth with the number of orders in a basket.
**Action:** Refactored to use `asyncio.gather()` for concurrent execution.
**Crucial Details:**
1. **Ordering:** Must maintain "BUYs then SELLs" execution order. Split into two `asyncio.gather` phases (Batch BUYs, await, then Batch SELLs).
2. **Concurrency Safety:** Each concurrent task must instantiate its own `AsyncSession` using `AsyncSessionLocal()` because SQLAlchemy sessions are not concurrency-safe.
3. **Resource Management:** Use `asyncio.Semaphore` to limit concurrent DB connections and avoid pool exhaustion.

## 2024-05-23 - Optimization of Dynamic Broker Imports
**Learning:** `holdings_service` and related services were rebuilding broker interface dictionaries on every call using `importlib.import_module` and `getattr`. This overhead is unnecessary for static modules.
**Action:** Applied `@functools.lru_cache` to `import_broker_module`.
**Crucial Details:**
1. **Speedup:** 43x speedup in micro-benchmark (~0.0059ms to ~0.0001ms).
2. **Safety:** Broker modules are static during runtime, so caching the interface dictionary is safe.
3. **Scope:** Applied to Holdings, Orderbook, Positionbook, and Tradebook services.
