## 2024-05-23 - Dynamic Import Overhead
**Learning:** `importlib.import_module` and subsequent `getattr` calls inside a hot loop (or frequently called function) add significant overhead, even if Python caches the modules. The overhead comes from function calls, string formatting, and dictionary construction.
**Action:** Use `functools.lru_cache` for functions that dynamically import modules and return their attributes, provided the returned objects are stateless (like module-level functions). This can yield ~99% performance improvement for that specific operation.
