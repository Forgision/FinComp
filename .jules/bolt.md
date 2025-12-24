## 2024-05-22 - Async Sequential Await in Analyze Mode
**Learning:** Found sequential `await` calls inside a loop for `sandbox_place_order` in `basket_order_service.py`. This caused linear latency growth with the number of orders in a basket.
**Action:** Refactored to use `asyncio.gather()` for concurrent execution.
**Crucial Details:**
1. **Ordering:** Must maintain "BUYs then SELLs" execution order. Split into two `asyncio.gather` phases (Batch BUYs, await, then Batch SELLs).
2. **Concurrency Safety:** Each concurrent task must instantiate its own `AsyncSession` using `AsyncSessionLocal()` because SQLAlchemy sessions are not concurrency-safe.
3. **Resource Management:** Use `asyncio.Semaphore` to limit concurrent DB connections and avoid pool exhaustion.

## 2025-12-24 - Sync Service in Async Route
**Learning:** `holdings_service.get_holdings` was a synchronous function attempting to call async dependencies (`get_auth_token_broker`) without awaiting them, and was being awaited by `orders.py` route handler. This would cause runtime errors and block the event loop if it worked synchronously.
**Action:** Refactored `holdings_service` to be fully `async def`, accepting `db: AsyncSession` explicitly.
**Crucial Details:**
1. **Async Propagation:** When a service needs to call an async DB function (like `get_auth_token_broker` or `get_analyze_mode`), the service function itself MUST be `async def`.
2. **Dynamic Imports:** Used `functools.lru_cache` for `import_broker_module` to avoid blocking I/O on repeated calls, as import operations can be slow.
3. **Correct Awaiting:** Ensure that dynamic broker function calls (e.g., `broker_funcs["get_holdings"]`) are awaited if the broker API is async.
