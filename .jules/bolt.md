## 2024-05-22 - Async Sequential Await in Analyze Mode
**Learning:** Found sequential `await` calls inside a loop for `sandbox_place_order` in `basket_order_service.py`. This caused linear latency growth with the number of orders in a basket.
**Action:** Refactored to use `asyncio.gather()` for concurrent execution.
**Crucial Details:**
1. **Ordering:** Must maintain "BUYs then SELLs" execution order. Split into two `asyncio.gather` phases (Batch BUYs, await, then Batch SELLs).
2. **Concurrency Safety:** Each concurrent task must instantiate its own `AsyncSession` using `AsyncSessionLocal()` because SQLAlchemy sessions are not concurrency-safe.
3. **Resource Management:** Use `asyncio.Semaphore` to limit concurrent DB connections and avoid pool exhaustion.
## 2026-01-04 - Cached Dynamic Broker Imports
**Learning:** Repeatedly calling `importlib.import_module` inside high-frequency service endpoints creates unnecessary overhead, even if Python caches modules in `sys.modules`. The string formatting and `getattr` lookups add up.
**Action:** Use `@functools.lru_cache` to cache the resulting dictionary of function references, reducing O(N) lookup/construction to O(1) for subsequent calls.
