## 2024-05-22 - Async Sequential Await in Analyze Mode
**Learning:** Found sequential `await` calls inside a loop for `sandbox_place_order` in `basket_order_service.py`. This caused linear latency growth with the number of orders in a basket.
**Action:** Refactored to use `asyncio.gather()` for concurrent execution.
**Crucial Details:**
1. **Ordering:** Must maintain "BUYs then SELLs" execution order. Split into two `asyncio.gather` phases (Batch BUYs, await, then Batch SELLs).
2. **Concurrency Safety:** Each concurrent task must instantiate its own `AsyncSession` using `AsyncSessionLocal()` because SQLAlchemy sessions are not concurrency-safe.
3. **Resource Management:** Use `asyncio.Semaphore` to limit concurrent DB connections and avoid pool exhaustion.

## 2024-05-22 - Redundant Dynamic Imports
**Learning:** `importlib.import_module` is cached by `sys.modules`, but services were re-executing `getattr` and dictionary construction logic on every request in `import_broker_module`.
**Action:** Applied `@functools.lru_cache` to `import_broker_module` in `holdings_service`, `orderbook_service`, `positionbook_service`, and `tradebook_service`.
**Crucial Details:**
1. **Cost:** Even with `sys.modules`, the overhead of multiple `getattr` calls and dictionary allocation adds up in high-throughput paths.
2. **Safety:** The return value is a dictionary of functions (effectively immutable references), so caching is safe provided the modules don't change at runtime (no hot-reloading requirement).
