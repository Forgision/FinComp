## 2024-05-22 - Async Sequential Await in Analyze Mode
**Learning:** Found sequential `await` calls inside a loop for `sandbox_place_order` in `basket_order_service.py`. This caused linear latency growth with the number of orders in a basket.
**Action:** Refactored to use `asyncio.gather()` for concurrent execution.
**Crucial Details:**
1. **Ordering:** Must maintain "BUYs then SELLs" execution order. Split into two `asyncio.gather` phases (Batch BUYs, await, then Batch SELLs).
2. **Concurrency Safety:** Each concurrent task must instantiate its own `AsyncSession` using `AsyncSessionLocal()` because SQLAlchemy sessions are not concurrency-safe.
3. **Resource Management:** Use `asyncio.Semaphore` to limit concurrent DB connections and avoid pool exhaustion.

## 2025-02-18 - Dynamic Import Overhead
**Learning:** `importlib.import_module` and `getattr` calls inside frequently accessed service methods (`get_holdings`, `get_orderbook`, etc.) add significant overhead even if the module is already in `sys.modules`.
**Action:** Use `@functools.lru_cache` to cache the result of the dynamic import logic.
**Crucial Details:**
1. **Cache Size:** `maxsize=32` is sufficient as the number of brokers is small and finite.
2. **Safety:** The returned dictionary of functions must be treated as immutable.
3. **Applicability:** Only apply to stateless services. Stateful services (like those instantiating classes per request) should not cache the factory function if it returns a new instance.
