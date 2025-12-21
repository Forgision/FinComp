## 2024-05-22 - Async Sequential Await in Analyze Mode
**Learning:** Found sequential `await` calls inside a loop for `sandbox_place_order` in `basket_order_service.py`. This caused linear latency growth with the number of orders in a basket.
**Action:** Refactored to use `asyncio.gather()` for concurrent execution.
**Crucial Details:**
1. **Ordering:** Must maintain "BUYs then SELLs" execution order. Split into two `asyncio.gather` phases (Batch BUYs, await, then Batch SELLs).
2. **Concurrency Safety:** Each concurrent task must instantiate its own `AsyncSession` using `AsyncSessionLocal()` because SQLAlchemy sessions are not concurrency-safe.
3. **Resource Management:** Use `asyncio.Semaphore` to limit concurrent DB connections and avoid pool exhaustion.

## 2024-12-21 - Dynamic Broker Import Overhead
**Learning:** Repeated calls to `importlib.import_module` and subsequent dictionary construction in core services (`holdings`, `orderbook`, etc.) caused significant overhead (~27µs per call). This is because `import_module` still involves function call overhead and lookups even if cached by `sys.modules`, and the services were reconstructing the function mapping dictionary on every single call.
**Action:** Applied `functools.lru_cache` to `import_broker_module`.
**Impact:** Reduced overhead to ~150ns (177x speedup).
