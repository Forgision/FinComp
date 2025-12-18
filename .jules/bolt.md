## 2024-05-22 - Async Sequential Await in Analyze Mode
**Learning:** Found sequential `await` calls inside a loop for `sandbox_place_order` in `basket_order_service.py`. This caused linear latency growth with the number of orders in a basket.
**Action:** Refactored to use `asyncio.gather()` for concurrent execution.
**Crucial Details:**
1. **Ordering:** Must maintain "BUYs then SELLs" execution order. Split into two `asyncio.gather` phases (Batch BUYs, await, then Batch SELLs).
2. **Concurrency Safety:** Each concurrent task must instantiate its own `AsyncSession` using `AsyncSessionLocal()` because SQLAlchemy sessions are not concurrency-safe.
3. **Resource Management:** Use `asyncio.Semaphore` to limit concurrent DB connections and avoid pool exhaustion.

## 2025-12-18 - Async Holdings Service
**Learning:** `get_holdings` service was synchronous but called async functions (`get_auth_token_broker`, `get_analyze_mode`) without awaiting, causing runtime errors and blocking the event loop.
**Action:** Refactored `holdings_service.py` to be fully `async`, utilizing `inspect` to handle both sync and async broker implementations dynamically.
