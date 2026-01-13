## 2024-05-22 - Async Sequential Await in Analyze Mode
**Learning:** Found sequential `await` calls inside a loop for `sandbox_place_order` in `basket_order_service.py`. This caused linear latency growth with the number of orders in a basket.
**Action:** Refactored to use `asyncio.gather()` for concurrent execution.
**Crucial Details:**
1. **Ordering:** Must maintain "BUYs then SELLs" execution order. Split into two `asyncio.gather` phases (Batch BUYs, await, then Batch SELLs).
2. **Concurrency Safety:** Each concurrent task must instantiate its own `AsyncSession` using `AsyncSessionLocal()` because SQLAlchemy sessions are not concurrency-safe.
3. **Resource Management:** Use `asyncio.Semaphore` to limit concurrent DB connections and avoid pool exhaustion.

## 2024-05-23 - Blocking Sync I/O in Async Routes (Analyzer Service)
**Learning:** `analyzer_service.py` functions were defined synchronously but used `AsyncSession`, causing potential runtime errors (coroutine objects not awaited) and blocking the event loop if they were to run. Frontend routes were also broken, not passing `db` sessions.
**Action:** Refactored `analyzer_service.py` to be fully `async`/`await`, ensuring non-blocking DB access. Updated frontend/backend routes to inject `db` and await service calls.
**Crucial Details:**
1. **Service Layer:** All services interacting with `AsyncSession` MUST be `async def`.
2. **Route Injection:** FastAPI routes must inject `db: AsyncSession` via `Depends(get_db)` and pass it to service functions.
3. **Code Duplication:** Centralizing logic in the service layer prevents "split-brain" implementations where backend/frontend routes drift apart.
