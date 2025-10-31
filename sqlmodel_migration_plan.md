# SQLModel Migration Plan

This document tracks the progress of migrating the project from SQLAlchemy to SQLModel.

## Phases

- [x] **Phase 1: Setup and Project Tracking**
  - [x] Create `sqlmodel_migration_plan.md`
  - [x] Add `sqlmodel` to `pyproject.toml` and install
  - [x] Centralize session management in `app/db/session.py`

- [ ] **Phase 2: Migrate `user_db` Module**
  - [ ] Move `app/core/schemas/user_db.py` to `app/core/models/user.py`
  - [ ] Convert `User` model to SQLModel
  - [ ] Refactor functions in `user.py`
  - [ ] Run user-related tests

- [ ] **Phase 3: Migrate Remaining Modules**
  - [ ] analyzer_db.py
  - [ ] apilog_db.py
  - [ ] auth_db.py
  - [ ] chartink_db.py
  - [ ] latency_db.py
  - [ ] master_contract_cache_hook.py
  - [ ] master_contract_status_db.py
  - [ ] sandbox_db.py
  - [ ] settings_db.py
  - [ ] strategy_db.py
  - [ ] telegram_db.py
  - [ ] token_db.py
  - [ ] token_db_enhanced.py
  - [ ] traffic_db.py

- [ ] **Phase 4: Final Cleanup and Verification**
  - [ ] Delete `app/core/schemas` directory
  - [ ] Run the full test suite

- [ ] **Phase 5: Submission**
  - [ ] Complete pre-commit steps
  - [ ] Submit the change
