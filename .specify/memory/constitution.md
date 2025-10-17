# OpenAlgo SpecKit Migration Constitution
<!-- 
This document outlines the non-negotiable principles and standards for the OpenAlgo SpecKit Migration project. 
Adherence to this constitution is mandatory for all contributions.
-->

<!--
Sync Impact Report:
- Version: 1.3.1 → 1.3.2
- Modified Principles:
  - V. Modular Architecture
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
The project is undergoing a strategic restructuring to align with the modular architecture defined in `.specify/memory/structure.md`. The current codebase, located in the `app/` directory, is in a transitional state and will be refactored to match the target structure. The legacy Flask-based project, located in the `.garbage/` directory, serves as a reference for existing functionalities. All new development and refactoring efforts MUST adhere to the target structure to ensure a consistent and maintainable codebase.

### VI. Component Interface Definitions
All broker integrations in `app/web/broker/` and trading algorithms in `app/algo/` MUST adhere to their respective defined interfaces. This ensures consistency, modularity, and allows for dynamic loading and execution of components.

### VII. Dependency and Environment Management
The project MUST use `uv` for managing the Python environment and requires Python version 3.12 or higher. New packages MUST be added using the `uv add` command. All Python scripts and modules MUST be executed using the `uv run` command to ensure they run within the project's managed environment.

### VIII. User Experience Consistency
All user-facing components MUST adhere to a consistent design language and user experience. This includes consistent naming, layout, and interaction patterns across the application. Any new UI components must be reviewed for consistency before implementation.

### IX. Frontend Technology Stack
The frontend MUST be built using HTML, JavaScript, and CSS. Server-side rendering MUST be implemented using Jinja2 templates, served via FastAPI. This ensures a clear separation of concerns between the frontend presentation layer and the backend API.

## Development Workflow

### Code Review and Quality Gates
All code contributions must be submitted via Pull Requests. A PR must be reviewed and approved by at least one other team member before merging. All automated checks (linting, testing, coverage) must pass.

## Governance

### Amendment Process
This constitution is the single source of truth for project standards. Any amendments require a formal proposal, review, and approval from the project leads. An approved amendment must include a migration plan for existing code if applicable. All changes will be reflected in the version number.

**Version**: 1.3.2 | **Ratified**: 2025-10-17 | **Last Amended**: 2025-10-17
