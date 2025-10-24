# OpenAlgo Project Structure

This document provides an overview of the directory structure for the current OpenAlgo project, which is built on FastApi. This file is used as a context for the model to understand the project structure.

## Directory Structure

```
/
├── app/                  # Main application container.
│   ├── __init__.py       # Initializes the Flask application.
│   ├── main.py           # Main Flask application instance and entry point.
│   ├── core/             # Core components shared across the application.
│   ├── db/               # Database related files (e.g., SQLAlchemy models).
│   ├── routes/           # Defines application routes and views.
│   ├── utils/            # Utility functions and helpers.
│   ├── web/              # Web-facing components.
│   ├── algo/             # Houses quantitative trading strategies and algorithms.
│   └── sandbox/          # Sandbox environment for testing or experimental features.
├── static/               # Static assets like compiled CSS, JavaScript, images.
│   ├── css/              # Compiled CSS files (e.g., main.css).
│   └── js/               # JavaScript files.
├── templates/            # Jinja2 templates for rendering HTML.
├── src/                  # Source files for frontend assets.
│   ├── css/              # Source CSS files (e.g., styles.css for Tailwind/DaisyUI).
│   └── js/               # Source JavaScript files.
├── test/                 # Contains all tests for the application (unit, integration, etc.).
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api_endpoints.py
│   ├── test_auth.py
│   ├── app/
│   ├── broker/
│   ├── core/
│   ├── integration/
│   ├── sandbox/
│   ├── unit/
│   └── websocket/
├── .env                  # Environment variable configuration for local development.
├── Dockerfile            # Defines the Docker image for the application.
├── docker-compose.yaml   # Orchestrates multi-container Docker applications for development.
├── pyproject.toml        # Project metadata and dependencies, managed by Poetry.
├── package.json          # Frontend dependencies and scripts (npm/yarn).
├── postcss.config.mjs    # PostCSS configuration for Tailwind CSS.
├── tailwind.config.mjs   # Tailwind CSS configuration.
├── start.sh              # Script to start the application.
└── README.md             # Project README.
```

## File Naming Conventions

- **Flask Blueprints/Routes:** `auth_routes.py`, `api_routes.py`
- **Database Models:** `user_model.py` (if using a separate file for models)
- **Services/Logic:** `user_service.py`

## Architectural Overview

The frontend serves all frontend-related files (HTML/JS/CSS/images) through Flask routes and communicates with the backend via a RESTful API. The backend uses services to perform actions and models to interact with the database.

## Technology Stack

- **Backend:** Python, FastApi, SQLAlchemy
- **Frontend:** JavaScript, Tailwind CSS, DaisyUI, PostCSS, Jinja2 templates
- **Database:** SQLite (or other relational database)
- **Real-time:** WebSockets, ZeroMQ

## Code Style and Linting

- **Formatter:** black
- **Linter:** ruff

## Environment Configuration

Environment variables are managed via a `.env` file and loaded within the Flask application.

## Restructuring Roadmap

1.  **Create a Test Suite:** Before making any changes to the application code, create a comprehensive test suite that covers the existing functionality. This test suite will serve as a safety net to ensure that the restructuring does not introduce any regressions. The tests should be placed in the `test/` directory.
2.  **Create New Directory Structure:** Once the test suite is in place and passing, create the new directories as defined in this document.
3.  **Move and Refactor Files:**
    *   Move existing files from the old structure to the new, corresponding locations.
    *   **Refactor Code:** After moving the files, refactor the code within them to align with the new structure. This includes:
        *   Moving classes, methods, and functions to their correct files based on the new architecture. For example, database schemas should be in `app/db/models/`, and business logic in `app/core/services/`.
        *   Splitting large files into smaller, more focused modules.
4.  **Refactor Imports:** Update all import statements in the moved and refactored files to reflect the new structure.
5.  **Update Configurations:** Ensure that all configurations (e.g., in `docker-compose.yaml`, `.ebextensions/`) are updated to point to the new file paths.
6.  **Run Tests and Static Analysis:**
    *   Continuously run the test suite throughout the process to ensure that the application is still functioning correctly.
    *   Run the linter (`ruff`) and formatter (`black`) to ensure the code adheres to the defined style.

## Component Interface Definitions

### Broker Interface

All broker integrations should adhere to a common interface to ensure consistency. A base class or a set of abstract methods should be defined for common operations like:

-   `connect()`
-   `place_order()`
-   `get_order_status()`
-   `get_positions()`
-   `get_funds()`

### Algorithm Interface

Similarly, all trading algorithms should follow a standard interface. This will allow the system to load and run algorithms dynamically. The interface should define methods for:

-   `initialize()`
-   `handle_data()`
-   `before_trading_start()`
-   `after_trading_end()`