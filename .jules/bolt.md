## 2025-12-16 - [Event Loop Blocking in Service Layer]
**Learning:** Found synchronous I/O calls (`broker_module.place_order_api`) inside `async def` service methods without `await` (for async) or `run_in_executor` (for sync). This blocks the asyncio event loop, degrading performance for all concurrent users.
**Action:** Use `inspect.iscoroutinefunction` to detect async implementations. Use `await` for coroutines and `asyncio.to_thread` for synchronous blocking calls to keep the loop non-blocking.
