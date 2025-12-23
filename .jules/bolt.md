## 2024-05-22 - Async Sequential Await in Analyze Mode
**Learning:** Found sequential `await` calls inside a loop for `sandbox_place_order` in `basket_order_service.py`. This caused linear latency growth with the number of orders in a basket.
**Action:** Refactored to use `asyncio.gather()` for concurrent execution.
**Crucial Details:**
1. **Ordering:** Must maintain "BUYs then SELLs" execution order. Split into two `asyncio.gather` phases (Batch BUYs, await, then Batch SELLs).
2. **Concurrency Safety:** Each concurrent task must instantiate its own `AsyncSession` using `AsyncSessionLocal()` because SQLAlchemy sessions are not concurrency-safe.
3. **Resource Management:** Use `asyncio.Semaphore` to limit concurrent DB connections and avoid pool exhaustion.

## 2025-12-23 - Sync Wrapper for Async Brokers
**Learning:** `holdings_service.py` was defined as synchronous but consumed by async routes and depended on async components (`get_analyze_mode`, async brokers). This caused `TypeError` when checking results (coroutines) and blocked the event loop.
**Action:** Refactored to `async def`, used `inspect.iscoroutinefunction` to handle both sync/async brokers, and offloaded sync calls to `loop.run_in_executor`.
