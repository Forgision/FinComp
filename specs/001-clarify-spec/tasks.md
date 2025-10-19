# Feature: Project Restructuring and Test Suite Implementation - Tasks

## Phase 1: Setup

### Story Goal
Initialize the project environment and establish the new directory structure.

### Independent Test Criteria
New directories are created as specified in the plan.

### Implementation Tasks
- [x] T001 Create `app/core/models/` directory
- [x] T002 Create `app/core/services/` directory
- [x] T003 Create `app/db/models/` directory
- [x] T004 Create `app/web/backend/routes/` directory
- [x] T005 Create `app/web/frontend/routes/` directory

## Phase 2: [US2] Restructure the project

### Story Goal
Reorganize the application's directory and file structure as per the new architecture.

### Independent Test Criteria
Files are moved to their correct new locations, and code within them is refactored to align with the new structure (e.g., Pydantic models in `app/core/models/`, business logic in `app/core/services/`, database schemas in `app/db/models/`).

### Implementation Tasks
- [ ] T006 [US2] Move Pydantic models to `app/core/models/` and refactor code
- [ ] T007 [US2] Move business logic to `app/core/services/` and refactor code
- [ ] T008 [US2] Move SQLAlchemy models to `app/db/models/` and refactor code
- [ ] T009 [US2] Move FastAPI routers to `app/web/backend/routes/` and refactor code
- [ ] T010 [US2] Move frontend routes to `app/web/frontend/routes/` and refactor code
- [ ] T011 [US2] Split large files into smaller, more focused modules as needed

## Phase 3: [US3] Update all imports

### Story Goal
Modify all import statements to reflect the new project structure.

### Independent Test Criteria
All import statements are updated and resolve correctly without errors.

### Implementation Tasks
- [ ] T012 [US3] Update import statements in `app/core/models/`
- [ ] T013 [US3] Update import statements in `app/core/services/`
- [ ] T014 [US3] Update import statements in `app/db/models/`
- [ ] T015 [US3] Update import statements in `app/web/backend/routes/`
- [ ] T016 [US3] Update import statements in `app/web/frontend/routes/`
- [ ] T017 [US3] Update import statements in `app/main.py`
- [ ] T018 [US3] Update import statements in `app/websocket/`
- [ ] T019 [US3] Update import statements in `app/sandbox/`
- [ ] T020 [US3] Update import statements in `app/broker/`

## Phase 4: [US4] Resolve issues & Fix Ruff Linting Errors

### Story Goal
Fix any problems or errors that arise from the restructuring process and resolve all Ruff linting errors.

### Independent Test Criteria
The application runs without runtime errors, and `ruff check .` reports no errors.

### Implementation Tasks
- [ ] T021 [US4] Fix any runtime errors resulting from restructuring
- [ ] T022 [US4] Generate Ruff error report: `uv run .specify/python-tools/check_ruff_errors.py`
- [ ] T023 [US4] Triage and prioritize Ruff errors: `uv run .specify/python-tools/categorize_ruff_errors.py`
- [ ] T024 [US4] Attempt automated Ruff fixes: `ruff --fix .`
- [ ] T025 [US4] Attempt unsafe automated Ruff fixes: `ruff --fix --unsafe-fixes .`
- [ ] T026 [US4] Manually fix remaining Ruff errors, repeating T022-T025 until no errors are found

## Phase 5: [US1] Verify with comprehensive test suite (Post-Restructuring)

### Story Goal
Execute the comprehensive test suite with unittest after restructuring to ensure no regressions and achieve 90% test coverage.

### Independent Test Criteria
All tests pass, and the project achieves a minimum of 90% test coverage.

### Implementation Tasks
- [ ] T027 [US1] Run all unit tests after restructuring
- [ ] T028 [US1] Generate test coverage report using `coverage.py`
- [ ] T029 [US1] Verify minimum 90% test coverage is achieved

## Phase 6: Polish & Cross-Cutting Concerns

### Story Goal
Ensure all configurations are updated and the project is ready for deployment in the new structure.

### Independent Test Criteria
`docker-compose.yml` and `.ebextensions/` are updated to reflect the new file paths.

### Implementation Tasks
- [ ] T030 Update `docker-compose.yml` to reflect new file paths
- [ ] T031 Update `.ebextensions/` configurations to reflect new file paths

## Phase 7: Foundational - Comprehensive Test Suite Setup (Pre-Restructuring)

### Story Goal
Establish a robust unit test suite and coverage measurement before any restructuring begins, to serve as a baseline.

### Independent Test Criteria
Unit tests are written for existing code, and a coverage report can be generated.

### Implementation Tasks
- [x] T032 Set up `unittest` framework in `test/`
- [x] T033 Set up `coverage.py` for test coverage measurement
- [x] T034 [P] Write initial unit tests for `app/main.py`
- [x] T035 [P] Write initial unit tests for `app/broker/finvasia/api/auth_api.py`
- [ ] T036 [P] Write initial unit tests for `app/broker/finvasia/api/data.py`
- [ ] T037 [P] Write initial unit tests for `app/broker/finvasia/api/funds.py`
- [ ] T038 [P] Write initial unit tests for `app/broker/finvasia/api/order_api.py`
- [ ] T039 [P] Write initial unit tests for `app/broker/finvasia/database/master_contract_db.py`
- [ ] T040 [P] Write initial unit tests for `app/broker/finvasia/mapping/order_data.py`
- [ ] T041 [P] Write initial unit tests for `app/broker/finvasia/mapping/transform_data.py`
- [ ] T042 [P] Write initial unit tests for `app/broker/finvasia/streaming/finvasia_adapter.py`
- [ ] T043 [P] Write initial unit tests for `app/broker/finvasia/streaming/finvasia_mapping.py`
- [ ] T044 [P] Write initial unit tests for `app/broker/finvasia/streaming/finvasia_websocket.py`
- [ ] T045 [P] Write initial unit tests for `app/db/base.py`
- [ ] T046 [P] Write initial unit tests for `app/db/models/analyzer_db.py`
- [ ] T047 [P] Write initial unit tests for `app/db/models/apilog_db.py`
- [ ] T048 [P] Write initial unit tests for `app/db/models/auth_db.py`
- [ ] T049 [P] Write initial unit tests for `app/db/models/base.py`
- [ ] T050 [P] Write initial unit tests for `app/db/models/chartink_db.py`
- [ ] T051 [P] Write initial unit tests for `app/db/models/latency_db.py`
- [ ] T052 [P] Write initial unit tests for `app/db/models/master_contract_cache_hook.py`
- [ ] T053 [P] Write initial unit tests for `app/db/models/master_contract_status_db.py`
- [ ] T054 [P] Write initial unit tests for `app/db/models/sandbox_db.py`
- [ ] T055 [P] Write initial unit tests for `app/db/models/session.py`
- [ ] T056 [P] Write initial unit tests for `app/db/models/settings_db.py`
- [ ] T057 [P] Write initial unit tests for `app/db/models/strategy_db.py`
- [ ] T058 [P] Write initial unit tests for `app/db/models/symbol.py`
- [ ] T059 [P] Write initial unit tests for `app/db/models/telegram_db.py`
- [ ] T060 [P] Write initial unit tests for `app/db/models/token_db_enhanced.py`
- [ ] T061 [P] Write initial unit tests for `app/db/models/token_db.py`
- [ ] T062 [P] Write initial unit tests for `app/db/models/traffic_db.py`
- [ ] T063 [P] Write initial unit tests for `app/db/models/tv_search.py`
- [ ] T064 [P] Write initial unit tests for `app/db/models/user_db.py`
- [ ] T065 [P] Write initial unit tests for `app/sandbox/execution_engine.py`
- [ ] T066 [P] Write initial unit tests for `app/sandbox/execution_thread.py`
- [ ] T067 [P] Write initial unit tests for `app/sandbox/fund_manager.py`
- [ ] T068 [P] Write initial unit tests for `app/sandbox/holdings_manager.py`
- [ ] T069 [P] Write initial unit tests for `app/sandbox/order_manager.py`
- [ ] T070 [P] Write initial unit tests for `app/sandbox/position_manager.py`
- [ ] T071 [P] Write initial unit tests for `app/sandbox/squareoff_manager.py`
- [ ] T072 [P] Write initial unit tests for `app/sandbox/squareoff_thread.py`
- [ ] T073 [P] Write initial unit tests for `app/websocket/base_adapter.py`
- [ ] T074 [P] Write initial unit tests for `app/websocket/broker_factory.py`
- [ ] T075 [P] Write initial unit tests for `app/websocket/fastapi_integration.py`
- [ ] T076 [P] Write initial unit tests for `app/websocket/mapping.py`
- [ ] T077 [P] Write initial unit tests for `app/websocket/port_check.py`
- [ ] T078 [P] Write initial unit tests for `app/websocket/server.py`
- [ ] T079 Run all initial unit tests and generate coverage report

## Dependencies
- Phase 1 must be completed before Phase 2.
- Phase 2 must be completed before Phase 3.
- Phase 3 must be completed before Phase 4.
- Phase 4 must be completed before Phase 5.
- Phase 5 must be completed before Phase 6.
- Phase 6 must be completed before Phase 7.

## Parallel Execution Examples
- **Phase 2 (US2):** Tasks T006-T010 can be executed in parallel as they involve moving and refactoring different logical components.
- **Phase 3 (US3):** Tasks T012-T020 can be executed in parallel as they involve updating imports in different directories.
- **Phase 7 (Foundational):** Tasks T034-T078 can be executed in parallel as they involve writing independent unit tests for different modules.

## Implementation Strategy
The implementation will follow an MVP-first approach, focusing on completing each user story incrementally. Each phase is designed to be an independently testable increment, allowing for continuous verification of correctness and stability throughout the restructuring process.