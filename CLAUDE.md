# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## High-Level Architecture

The project is a FastAPI-based web application with a modular structure:

*   **`app/core/`**: Contains core components and services shared across the application, including Pydantic models for request/response validation and business logic in services.
*   **`app/db/`**: Manages database-related files, including SQLAlchemy models for CRUD operations.
*   **`app/web/`**: Houses web-facing components. This includes:
    *   **`app/web/main.py`**: The main FastAPI application instance.
    *   **`app/web/backend/`**: Defines API endpoints consumed by the frontend.
    *   **`app/web/frontend/`**: Contains HTML templates (Jinja2), CSS, JavaScript, static assets, and routes for web pages.
    *   **`app/web/broker/`**: Integrations with third-party broker APIs.
    *   **`app/web/websocket/`**: Real-time communication layer using WebSockets.
*   **`app/algo/`**: Stores quantitative trading strategies and algorithms.
*   **`test/`**: Contains all unit and integration tests.

The application uses environment variables for configuration (`.env`).

## Commonly Used Commands

These commands use `uv` for consistent environment management.

*   **Install Dependencies**: `uv add <package_name>` or `uv pip install -r requirements.txt`
*   **Run the Application (Development)**: `uv run uvicorn app.main:app --reload`
*   **Run All Tests**: `uv run pytest`
*   **Run a Single Test File**: `uv run pytest <path_to_test_file>` (e.g., `uv run pytest test/unit/app/core/models/test_tradingview_models.py`)
*   **Run Linter (Ruff)**: `uv run ruff check .`
*   **Run Formatter (Black)**: `uv run black .`
*   **Activate Virtual Environment**: `source .venv/bin/activate`

## Developement/Implementation Rules
- Use `logger` instance from `app.utils.logging` instead of `get_logger` from the module.
- All development MUST adhere to the directory and file structure defined in `.specify/memory/structure.md`.