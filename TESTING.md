# FinComp Testing Standards

This document outlines the testing philosophy, standards, and practices for the FinComp project. All contributors are expected to adhere to these guidelines to ensure the reliability, maintainability, and quality of the codebase.

## 1. Testing Philosophy

We believe in a comprehensive testing strategy that combines unit, integration, and end-to-end tests to catch bugs early, prevent regressions, and enable confident refactoring. Every new feature should be accompanied by tests, and bug fixes should include a regression test.

## 2. Tools

- **Test Framework**: [Pytest](https://pytest.org) is the standard test framework for this project.
- **Test Runner**: Tests should be executed using the `pytest` command, preferably run via `uv`: `uv run pytest`.

## 3. Test Types and Directory Structure

The `test/` directory is organized by test type to maintain a clear separation of concerns.

### a. Unit Tests

- **Purpose**: To test individual functions, classes, or components in isolation. They should be fast and have no external dependencies (e.g., no database or network calls).
- **Location**: `test/unit/`
- **Structure**: The directory structure within `test/unit/` should mirror the application's structure. For example, a unit test for a model in `app/core/models/my_model.py` should be located at `test/unit/app/core/models/test_my_model.py`.

### b. Integration Tests

- **Purpose**: To test the interaction between multiple components or services. These tests are allowed to have external dependencies, such as a test database or mock APIs.
- **Location**: `test/integration/`
- **Structure**: Tests should be organized by the features or services they integrate.

### c. End-to-End (E2E) / Sandbox Tests

- **Purpose**: To test the application from the user's perspective, simulating real-world scenarios. These are the most comprehensive tests, covering the full application stack. The existing `test/sandbox/` directory serves this purpose.
- **Location**: `test/sandbox/`

## 4. File and Test Naming Conventions

- **Test Files**: Test files must be named using the `test_*.py` prefix (e.g., `test_authentication.py`).
- **Test Functions**: Test functions within these files must be named using the `test_*` prefix (e.g., `def test_user_can_login():`).

## 5. How to Run Tests

Ensure you have installed the development dependencies first:
```bash
uv add <package_name> --dev # Assuming a [dev] extra in pyproject.toml
```

### a. Run All Tests

To run the entire test suite:
```bash
uv run pytest
```

### b. Run Specific Tests

- **Run a specific test file**:
  ```bash
  uv run pytest test/unit/app/core/models/test_tradingview_models.py
  ```
- **Run tests in a directory**:
  ```bash
  uv run pytest test/integration/
  ```
- **Run a specific test by keyword**:
  ```bash
  uv run pytest -k "login"
  ```

## 6. Test Coverage

While not yet enforced, the goal is to maintain a high level of test coverage. We will be integrating a coverage tool (like `pytest-cov`) into our CI pipeline in the future to measure and report on this. All new code should strive for a minimum of 80% test coverage.

## 7. Handling Flaky Tests

Flaky tests are tests that occasionally pass and occasionally fail without any code changes. They are a significant source of frustration and can undermine confidence in the test suite. This section outlines the process for identifying, fixing, and quarantining flaky tests.

### a. Identification

- **CI/CD Monitoring**: Flaky tests are often identified through inconsistent failures in the CI/CD pipeline. Tools that track test history can help pinpoint frequently failing tests.
- **Local Reproduction**: Developers should attempt to reproduce flaky test failures locally multiple times.

### b. Fixing Flaky Tests

- **Isolate the Flakiness**: Determine the root cause of the flakiness. Common causes include:
    - **Race Conditions**: Tests that depend on the order of execution or timing.
    - **External Dependencies**: Tests that rely on external services or resources that are not consistently available or return variable data.
    - **Improper Teardown**: Tests that leave behind state that affects subsequent tests.
    - **Randomness**: Tests that use random data without proper seeding.
- **Stabilize the Test**: Implement changes to make the test deterministic:
    - Use mocks or stubs for external dependencies.
    - Ensure proper setup and teardown to isolate test runs.
    - Use fixed seeds for random number generators.
    - Avoid relying on specific execution order of tests.

### c. Quarantining Flaky Tests

If a flaky test cannot be immediately fixed, it should be quarantined to prevent it from blocking the CI/CD pipeline and eroding developer confidence. Quarantined tests should be:

- **Marked**: Use `pytest.mark.flaky` (if using `pytest-rerunfailures` or similar plugin) or `pytest.mark.skip` with a clear reason and a link to an issue.
- **Tracked**: Create an issue in the project's issue tracker to track the flaky test and prioritize its fix.
- **Run Separately (Optional)**: In some cases, flaky tests might be run on a less frequent schedule or in a dedicated pipeline to monitor their behavior without impacting the main CI/CD flow.

**Example of marking a flaky test:**

```python
import pytest

@pytest.mark.flaky(reruns=5, reruns_delay=2)
def test_flaky_function():
    # Test logic that might sometimes fail
    assert some_flaky_operation()
```

**Note**: The goal is always to fix flaky tests, not to permanently quarantine them. Quarantining is a temporary measure to maintain productivity while a fix is being developed.
