# Claude Agent Context: FinComp Project

This document provides essential context for operating on the FinComp codebase. Adherence to these guidelines is critical for maintaining code quality, consistency, and stability.

## 1. Core Technologies & Frameworks

- **Web Framework**: FastAPI is the standard for all API development.
- **Data Validation**: Pydantic is used for all data validation, serialization, and settings management. Define clear schemas in `app.core.models` for all API requests and responses.
- **Database**: The project is set up to use SQLAlchemy for database interactions, although the primary models encountered so far have been Pydantic. Keep a clear distinction between Pydantic API models (`app.core.models`) and SQLAlchemy DB models (`app/db/models`).
- **Containerization**: The application is containerized using Docker and orchestrated with Docker Compose. All services should be defined in `docker-compose.yml`.

## 2. Tooling and Commands

- **Package & Environment Management**: This project uses `uv`. **Do not use `poetry` or `pip` directly for running scripts.**
  - Install dependencies: `uv pip install -r requirements.txt` (or similar `uv add <package_name>` command)
  - Run scripts: `uv run <script_name>` (e.g., `uv run ruff check .`)

- **Code Quality (Linting & Formatting)**: `ruff` is the single tool for linting and formatting.
  - **Linting**: Run `uv run ruff check .` to identify issues. All code must pass linting before being committed.
  - **Formatting**: Run `uv run ruff format .` to format the code according to project standards.

## 3. Style and Conventions

- **Coding Style**:
  - Adhere strictly to **PEP 8**.
  - Follow formatting standards compatible with `black`. `ruff format .` handles this automatically.
  - **Static Typing**: All new code MUST include type hints. Aim for 100% type coverage on new functions.

- **Docstrings**:
  - All public modules, functions, classes, and methods MUST have docstrings.
  - The required format is the **Google Python Style Guide**.

- **Error Handling**:
  - All API endpoints must return standardized error responses.
  - Use the `BaseErrorResponse` model from `app.core.models.error_models.py` when raising `HTTPException`.
  - Example: `raise HTTPException(status_code=404, detail=BaseErrorResponse(message="Item not found").model_dump())`

- **Logging**:
  - Use the centralized logger provided in `app/utils/logging.py`.
  - Get a logger instance at the top of each module: `from app.utils.logging import logger`.

- **Commits and Pull Requests**:
  - Follow conventional commit message standards (e.g., `feat:`, `fix:`, `refactor:`).
  - Ensure PR descriptions are clear and link to the relevant issue or task.

## 4. Tool Usage Notes

- When editing files, especially for multi-line changes like adding docstrings, the `Edit` tool can be unreliable if the `old_string` is not unique or contains complex formatting.
- **Robust Strategy**: If `Edit` fails or produces incorrect results (e.g., duplicated content), switch to a `Read` -> (manual reconstruction) -> `Write` pattern. Read the entire file, correct it in memory, and then use `Write` to overwrite it with the correct content. This is more reliable for complex changes.
