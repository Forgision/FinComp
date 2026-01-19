## 2024-05-22 - Async Sequential Await in Analyze Mode
**Learning:** Found sequential `await` calls inside a loop for `sandbox_place_order` in `basket_order_service.py`. This caused linear latency growth with the number of orders in a basket.
**Action:** Refactored to use `asyncio.gather()` for concurrent execution.
**Crucial Details:**
1. **Ordering:** Must maintain "BUYs then SELLs" execution order. Split into two `asyncio.gather` phases (Batch BUYs, await, then Batch SELLs).
2. **Concurrency Safety:** Each concurrent task must instantiate its own `AsyncSession` using `AsyncSessionLocal()` because SQLAlchemy sessions are not concurrency-safe.
3. **Resource Management:** Use `asyncio.Semaphore` to limit concurrent DB connections and avoid pool exhaustion.

## 2025-01-19 - Synchronous Service Logic in Async Architecture
**Learning:** `analyzer_service.py` functions were defined synchronously but used `AsyncSession`, returning unawaited coroutines when calling `db.execute()`. This caused runtime errors and forced the route layer to duplicate the logic correctly.
**Action:** Refactored service functions to be `async def` and explicitly `await` database calls. Updated all consumers to inject `db` dependency and `await` service calls.
**Crucial Details:**
1. **Dependency Injection:** Services depending on `db` must accept it as an argument, and routes must inject it via `Depends(get_db)`.
2. **Code Duplication:** Removing duplicated logic from controllers/routes prevents "drift" where fixes in one place aren't applied to another.
3. **Type Safety:** Correct type hints (`db: AsyncSession`) help identifying such issues, but static analysis (mypy) needs correct configuration to catch them effectively.
