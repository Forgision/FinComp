# To-Do List

## High Priority
- [x] **Fix Startup Error:** Resolve the `pydantic ValidationError` and subsequent `ValueError` preventing the application from starting.
  - [x] **Diagnose Root Cause (ValidationError):** Identified that an empty `CSRF_TIME_LIMIT` in the `.env` file caused a type validation failure.
  - [x] **Apply Fix (ValidationError):** Removed the invalid `CSRF_TIME_LIMIT` line from the `.env` file.
  - [x] **Diagnose Root Cause (ValueError):** Identified that inline comments and quotes in the `.env` file were causing parsing errors for `LOG_RETENTION` and other variables.
  - [x] **Apply Fix (ValueError):** Cleaned up the `.env` file by removing inline comments and quotes from multiple variables.
  - [-] **Verify Fix:** Awaiting user confirmation that the application now starts successfully.