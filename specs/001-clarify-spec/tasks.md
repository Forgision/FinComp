# Tasks: Project Restructuring and Test Suite Implementation

This document outlines the tasks required to restructure the project and implement a comprehensive test suite.

## Phase 1: Setup

- [ ] T001 Install testing dependencies: `uv add unittest coverage.py`
- [ ] T002 Configure `coverage.py` in `pyproject.toml` to achieve 90% coverage.

## Phase 2: Foundational - Test Suite Creation (Pre-Restructuring)

- [ ] T003 Create unit tests for `app/web/main.py` in `test/web/test_main.py`.
- [ ] T004 Create unit tests for `app/web/broker/` components in `test/web/broker/`.
- [ ] T005 Create unit tests for `app/web/sandbox/` components in `test/web/sandbox/`.
- [ ] T006 Create unit tests for `app/web/websocket/` components in `test/web/websocket/`.
- [ ] T007 Run initial test suite and generate a coverage report: `uv run coverage run -m unittest discover test && uv run coverage report -m`
- [ ] T008 Verify that the initial test coverage is at least 90%.

## Phase 3: Restructuring

- [ ] T009 Create the new directory structure as defined in `specs/001-clarify-spec/plan.md`.
- [ ] T010 Move `app/web/broker/` subdirectories to `app/broker/`.
- [ ] T010a Move `app/web/sandbox/` contents to `app/sandbox/`.
- [ ] T010b Move `app/web/websocket/` contents to `app/websocket/`.
- [ ] T010c Move other `app/web/` files to their corresponding new locations in `app/`.

## Phase 4: Refactoring

- [ ] T011 Update all import statements in the moved files to reflect the new project structure.
- [ ] T011a Refactor `app/web/main.py` into `app/main.py` and update its dependencies.
- [ ] T012 Move database schemas to `app/db/models/`.
- [ ] T014a Refactor files by moving classes, methods, and functions to their correct modules as per the new architecture.
- [ ] T013 Move Pydantic models to `app/core/models/`.
- [ ] T014 Move business logic to `app/core/services/`.

## Phase 5: Validation (Post-Restructuring)

- [ ] T015 Update the test suite to reflect the new project structure.
- [ ] T016 Run the updated test suite and ensure all tests pass: `uv run coverage run -m unittest discover test && uv run coverage report -m`
- [ ] T017 Run static analysis to ensure code quality: `ruff check .`

- [ ] T017a Create performance tests to benchmark critical code paths.
- [ ] T017b Run performance tests and verify that the application meets the 100 requests/second goal.
## Phase 6: Polish & Cross-cutting Concerns

- [ ] T018 Update `docker-compose.yml` and `.ebextensions/` with new file paths.
- [ ] T019 Review and finalize the restructured project.

## Dependencies

- **Phase 2** depends on **Phase 1**.
- **Phase 3** depends on **Phase 2**.
- **Phase 4** depends on **Phase 3**.
- **Phase 5** depends on **Phase 4**.
- **Phase 6** depends on **Phase 5**.

## Implementation Strategy

The implementation will follow the phases outlined above. Each phase must be completed before the next one begins. The test suite will be the primary tool for ensuring the stability of the application throughout the restructuring process.