# OpenAlgo Project Structure

This document provides an overview of the directory structure for the current OpenAlgo project, which is built on FastAPI. This file is used as a context for the model to understand the project structure.

## Directory Structure

```
/
├── app/                  # Main application container.
│   ├── core/             # Core components shared across the application.
│   │   ├── models/       # Pydantic models for request/response validation and data transfer objects (DTOs).
│   │   └── services/     # Implements the business logic, decoupling the API from the database. Contains CRUD operations and other data processing tasks.
│   ├── db/               # Database related files
│   │   └── models/       # Database schemas (SQLAlchemy models).
│   ├── web/              # Web-facing components, including the API and frontend.
│   │   ├── main.py       # The main FastAPI application instance and entry point.
│   │   ├── backend/      # API endpoints (routes) that the frontend consumes. Handles HTTP requests and responses.
│   │   ├── broker/       # Contains integrations with third-party broker APIs.
│   │   ├── frontend/     # All frontend-related code: HTML templates, CSS, JavaScript, and static assets. Also includes routes that serve web pages.
│   │   └── websocket/    # Real-time communication layer using WebSockets.
│   └── algo/             # Houses quantitative trading strategies and algorithms.
├── test/                 # Contains all tests for the application (unit, integration, etc.).
├── .env                  # Environment variable configuration for local development.
├── Dockerfile            # Defines the Docker image for the application.
├── docker-compose.yml    # Orchestrates multi-container Docker applications for development.
└── pyproject.toml        # Project metadata and dependencies, managed by Poetry.
```

## File Naming Conventions

- **Services:** `user_service.py`
- **Schemas/Models:** `user_schema.py` or `user_model.py`

## Architectural Overview

The frontend serves all frontend-related files (HTML/JS/CSS/images) through routes and communicates with the backend via a RESTful API. The backend uses services to perform actions and models to validate responses.

## Technology Stack

- **Database:** SQLite with SQLAlchemy
- **Backend:** FastAPI
- **Frontend:** Jinja2 templates with HTML, JS, CSS

## Code Style and Linting

- **Formatter:** black
- **Linter:** ruff

## Environment Configuration

Environment variables are managed via a `.env` file and loaded in `app/core/config.py`.

## Restructuring Roadmap

1.  **Create a Test Suite:** Before making any changes to the application code, create a comprehensive test suite that covers the existing functionality. This test suite will serve as a safety net to ensure that the restructuring does not introduce any regressions. The tests should be placed in the `test/` directory.
2.  **Create New Directory Structure:** Once the test suite is in place and passing, create the new directories as defined in this document.
3.  **Move and Refactor Files:**
    *   Move existing files from the old structure to the new, corresponding locations.
    *   **Refactor Code:** After moving the files, refactor the code within them to align with the new structure. This includes:
        *   Moving classes, methods, and functions to their correct files based on the new architecture. For example, database schemas should be in `app/db/models/`, Pydantic models in `app/core/models/`, and business logic in `app/core/services/`.
        *   Splitting large files into smaller, more focused modules.
4.  **Refactor Imports:** Update all import statements in the moved and refactored files to reflect the new structure.
5.  **Update Configurations:** Ensure that all configurations (e.g., in `docker-compose.yml`, `.ebextensions/`) are updated to point to the new file paths.
6.  **Run Tests and Static Analysis:**
    *   Continuously run the test suite throughout the process to ensure that the application is still functioning correctly.
    *   Run the linter (`ruff`) and formatter (`black`) to ensure the code adheres to the defined style.

## Component Interface Definitions

### Broker Interface

All broker integrations in the `app/web/broker/` directory should adhere to a common interface to ensure consistency. A base class or a set of abstract methods should be defined for common operations like:

-   `connect()`
-   `place_order()`
-   `get_order_status()`
-   `get_positions()`
-   `get_funds()`

### Algorithm Interface

Similarly, all trading algorithms in the `app/algo/` directory should follow a standard interface. This will allow the system to load and run algorithms dynamically. The interface should define methods for:

-   `initialize()`
-   `handle_data()`
-   `before_trading_start()`
-   `after_trading_end()`
