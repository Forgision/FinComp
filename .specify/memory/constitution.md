# OpenAlgo SpecKit Migration Constitution
<!-- 
This document outlines the non-negotiable principles and standards for the OpenAlgo SpecKit Migration project. 
Adherence to this constitution is mandatory for all contributions.
-->

<!--
Sync Impact Report:
- Version: 1.6.0 -> 1.7.0
- Change: Merged sections "X. Iterative Linting Error Resolution" and "XI. Error Resolution Policy" into a single "X. Linting and Error Resolution Policy" to remove redundancy.
- Templates requiring updates:
  - [ ] .specify/templates/plan-template.md
  - [ ] .specify/templates/spec-template.md
  - [ ] .specify/templates/tasks-template.md
-->

## Core Principles

### I. Strict Code Quality
All code MUST adhere to PEP 8 standards. Automated linting and formatting are enforced through pre-commit hooks using `ruff` for linting and `black` for formatting. Naming conventions are strictly followed: `PascalCase` for classes and Pydantic models, and `snake_case` for functions, methods, and variables.

### II. Comprehensive Testing
Test-Driven Development (TDD) is non-negotiable. Tests MUST be written before the implementation code. A minimum of 90% code coverage is required for all core business logic. Unittest is the sole testing framework for this project.

### III. API Design and Consistency
All APIs MUST be RESTful. Endpoints should have clear, consistent, and predictable naming schemes. Pydantic models MUST be used for all request and response data validation to ensure type safety and clear contracts.

### IV. Performance as a Feature
Code must be written with performance considerations in mind. Critical code paths and database queries should be benchmarked and optimized. Any feature that introduces a significant performance regression requires explicit justification and approval.

### V. Modular Architecture
The project MUST adhere to the modular architecture defined in `.specify/memory/structure.md`. The core structure is organized as follows:
*   `app/core/`: Contains shared components, including Pydantic models (`models/`) for data transfer and business logic (`services/`).
*   `app/db/`: Manages database interactions, with SQLAlchemy schemas in `models/`.
*   `app/web/`: Contains all web-facing components, including the main FastAPI application (`main.py`), API endpoints (`backend/`), frontend templates and routes (`frontend/`), WebSocket communication (`websocket/`), and third-party broker integrations (`broker/`).
*   `app/algo/`: Houses all quantitative trading strategies and algorithms.
*   `test/`: Contains all tests for the application.
All new development and refactoring efforts MUST conform to this structure.

### VI. Component Interface Definitions
All components MUST adhere to their defined interfaces to ensure consistency and modularity.
*   **Broker Interface (`app/web/broker/`):** Integrations MUST implement a common interface for operations such as `connect()`, `place_order()`, `get_order_status()`, `get_positions()`, and `get_funds()`.
*   **Algorithm Interface (`app/algo/`):** Trading algorithms MUST follow a standard interface with methods for `initialize()`, `handle_data()`, `before_trading_start()`, and `after_trading_end()`.

### VII. Dependency and Environment Management
The project MUST use `uv` for managing the Python environment and requires Python version 3.12 or higher. New packages MUST be added using the `uv add` command. All Python scripts and modules MUST be executed using the `uv run` command to ensure they run within the project's managed environment.

### VIII. User Experience Consistency
All user-facing components MUST adhere to a consistent design language and user experience. This includes consistent naming, layout, and interaction patterns across the application. Any new UI components must be reviewed for consistency before implementation.

### IX. Frontend Technology Stack
The frontend MUST be built using HTML, JavaScript, and CSS. Server-side rendering MUST be implemented using Jinja2 templates, served via FastAPI. This ensures a clear separation of concerns between the frontend presentation layer and the backend API.

### X. Linting and Error Resolution Policy
All `ruff` linting errors MUST be resolved using the systematic, iterative workflow defined in `.kilocode/rules/ruff-linting-strategy.md`. This process is non-negotiable for maintaining code quality and codifies our approach to technical debt. The core workflow is as follows:

1.  **Generate Report**: Create a comprehensive error report to establish a baseline for the current state of linting issues.
    ```bash
    uv run .specify/python-tools/check_ruff_errors.py
    ```

2.  **Triage and Prioritize**: Analyze the report to identify and prioritize the most frequent error codes for efficient resolution.
    ```bash
    uv run .specify/python-tools/categorize_ruff_errors.py
    ```

3.  **Automated Fixes**: Always attempt automated correction first. Run the following commands in sequence to apply both safe and unsafe fixes:
    ```bash
    # Apply standard, safe fixes
    ruff --fix .
    # Apply unsafe fixes (e.g., for unused imports)
    ruff --fix --unsafe-fixes .
    ```

4.  **Manual Fixes**: For errors that persist after automated attempts, perform surgical manual fixes. Use targeted tools like `apply_diff` instead of rewriting entire files.

5.  **Validate and Repeat**: After each round of fixes, return to Step 1 to generate a new report and repeat the cycle until no errors remain.

## Development Workflow

### Code Review and Quality Gates
All code contributions must be submitted via Pull Requests. A PR must be reviewed and approved by at least one other team member before merging. All automated checks (linting, testing, coverage) must pass.

## Governance

### Amendment Process
This constitution is the single source of truth for project standards. Any amendments require a formal proposal, review, and approval from the project leads. An approved amendment must include a migration plan for existing code if applicable. All changes will be reflected in the version number.

**Version**: 1.7.0 | **Ratified**: 2025-10-17 | **Last Amended**: 2025-10-18