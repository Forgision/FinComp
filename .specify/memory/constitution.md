<!--
Sync Impact Report:
- Version change: 1.2.0 -> 1.3.0
- List of modified principles: None
- Added sections:
    - XI. Code Documentation
    - XII. Static Typing
- Removed sections: None
- Templates requiring updates:
    - ✅ README.md
- Follow-up TODOs:
    - TODO(RATIFICATION_DATE): Determine the original adoption date of these principles.
-->
# OpenAlgo Constitution

## Core Principles

### I. Technology Stack
The project is a hybrid, with a Python/FastAPI backend and a JavaScript/CSS frontend. Development must respect the conventions and tooling of both ecosystems. The legacy Flask application is preserved for reference in the `.garbage/` directory and MUST NOT be modified or deleted.

### II. Strict Project Structure
All development MUST adhere to the directory and file structure defined in `.specify/memory/structure.md`. This includes conventions for services, models, and routes. New features must be implemented in the appropriate layer to maintain this structure.

### III. API-First Design
The application provides a RESTful API with a unified structure. All core functionality should be exposed through this API first, before being consumed by the frontend or other clients. This ensures that the application can be used headless or with alternative frontends.

### IV. Declarative Configuration
Project configuration (for linting, building, and packaging) is managed through declarative files (e.g., `ruff.toml`, `pyproject.toml`, `tailwind.config.mjs`). Avoid hardcoding configuration values in the code.

### V. Comprehensive Testing
A dedicated `test/` directory exists with subdirectories for unit, integration, and other types of tests. All new features or bug fixes must be accompanied by corresponding tests to ensure correctness and prevent regressions.

### VI. Standardized Tooling
`uv` MUST be used for all Python environment management and script execution. Dependencies MUST be added with `uv add` and scripts run with `uv run`.

### VII. Centralized Logging
All logging MUST use the `logger` method from the `app.utils.logging` module. Creating new logger instances directly is forbidden.

### VIII. Strict Code Quality
All Python code MUST adhere to PEP 8 standards. Code MUST be formatted with `black` and linted with `ruff` before committing.

### IX. Comprehensive Unit Testing
All new code MUST be accompanied by unit tests using Python's `unittest` framework. A high level of code coverage is expected and will be enforced.

### X. User Experience Consistency
The user interface MUST adhere to the design system established by DaisyUI to ensure a consistent and intuitive user experience across the application.

### XI. Code Documentation
All public APIs, complex functions, and business logic MUST be documented using docstrings following the Google Python Style Guide.

### XII. Static Typing
All new Python code MUST use type hints for function signatures and variables to improve code clarity and allow for static analysis.

## Frontend Development

Frontend styling is managed with Tailwind CSS and DaisyUI. The source CSS file is `app/web/frontend/static/css`. All UI components should adhere to the design system established by DaisyUI.

## Backend Development

The backend is a FastAPI application run with `uvicorn`. The application is started using `uv run uvicorn app.main:app --reload`. Code must be compliant with the rules defined in `ruff.toml`.

## Governance

All changes must be compliant with the principles outlined in this constitution. Code reviews are mandatory and must verify adherence to the project's architecture and conventions.

**Version**: 1.3.0 | **Ratified**: TODO(2025-10-18): Determine the original adoption date of these principles. | **Last Amended**: 2025-10-20
