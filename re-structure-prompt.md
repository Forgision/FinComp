# Project Restructuring Guide for OpenAlgo

## Objective

Your primary task is to restructure the OpenAlgo project. You will transform the project from its current directory layout to the new, well-defined architecture described in the `structure.md` file. This is a significant undertaking that involves not just moving files, but also carefully refactoring the code within them to align with the new design principles. The ultimate goal is a cleaner, more maintainable codebase that remains fully functional.

## Key Resources

### 1. Target Architecture (`structure.md`)

This is your blueprint. It defines the target directory structure, component responsibilities, file naming conventions, and architectural patterns. You must adhere to it strictly.

```
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
```

### 2. Current Project Structure

Here is a snapshot of the current project structure for your reference:

```
.
├── app
│   ├── core
│   │   ├── config.py
│   │   ├── middleware.py
│   │   └── __pycache__
│   ├── db
│   │   ├── analyzer_db.py
│   │   ├── apilog_db.py
│   │   ├── auth_db copy.py
│   │   ├── auth_db.py
│   │   ├── base.py
│   │   ├── chartink_db.py
│   │   ├── __init__.py
│   │   ├── latency_db.py
│   │   ├── master_contract_cache_hook.py
│   │   ├── master_contract_status_db.py
│ s  │   ├── models
│   │   ├── __pycache__
│   │   ├── sandbox_db.py
│   │   ├── session.py
│   │   ├── settings_db.py
│   │   ├── strategy_db.py
│   │   ├── symbol.py
│   │   ├── telegram_db.py
│   │   ├── token_db_backup.py
│   │   ├── token_db_enhanced.py
│   │   ├── token_db.py
│a   │   ├── traffic_db.py
│   │   ├── tv_search.py
│   │   ├── user_db copy.py
│   │   └── user_db.py
│   ├── __init__.py
│   ├── __pycache__
│   ├── utils
│   │   ├── api_analyzer.py
│   │   ├── auth_utils.py
│   │   ├── constants.py
│   │   ├── email_debug.py
│   │   ├── email_utils.py
│   │   ├── env_check.py
│   │_   ├── httpx_client.py
│   │   ├── __init__.py
│   │   ├── ip_helper.py
│   │   ├── latency_monitor.py
│   │   ├── logger.py
│   │   ├── logging copy.py
│   │   ├── logging.py
│   │   ├── number_formatter.py
│   │   ├── plugin_loader.py
│   │a   ├── __pycache__
│   │   ├── security_middleware.py
│   │   ├── session.py
│   │   ├── socketio_error_handler.py
│   │   ├── traffic_logger.py
│   │   ├── version.py
│   │   └── web
│   └── web
│       ├── backend
│       ├── broker
│       ├── frontend
│       ├── __init__.py
│       ├── main.py
│       ├── models
│       ├── __pycache__
│       ├── sandbox
│       ├── services
│       └── websocket
├── db
│   ├── latency.db
│   ├── logs.db
│   ├── openalgo.db
│   ├── sandbox.db
│   └── telegram.db
├── docker-compose.yaml
├── Dockerfile
├── __init__.py
├── INSTALL.md
├── keys
├── License.md
├── log
│   └── strategies
├── openalgoUI.egg-info
│   ├── dependency_links.txt
│   ├── PKG-INFO
│   ├── requires.txt
│   ├── SOURCES.txt
│   └── top_level.txt
├── package.json
├── package-lock.json
├── postcss.config.mjs
├── __pycache__
│   └── test.cpython-312.pyc
├── pyproject.toml
├── README.md
├── SECURITY.md
├── start.sh
├── strategies
│   └── scripts
├── structure.md
├── tailwind.config.mjs
├── test.py
├── test-two.py
└── uv.lock
```

## Core Instructions

You must follow the "Restructuring Roadmap" outlined in `structure.md`.

## Guiding Principles for Execution

*   **Methodical Approach:** Follow the roadmap step-by-step. This is a sequential process.
*   **Precision in Refactoring:** When refactoring, be extremely careful. Your goal is to reorganize, not to rewrite logic. Pay close attention to dependencies between components to avoid breaking functionality.
*   **Continuous Verification:** After each major step, especially after refactoring, you must verify your work. Use the project's test suite (that you will create) to ensure that the application remains stable.
*   **Clear Communication:** Provide clear and concise updates on your progress. If you encounter any ambiguities or issues that you cannot resolve, you must ask for clarification.

## Final Goal

The project must be fully functional and strictly adhere to the new architecture defined in `structure.md`. All newly created tests must pass, and the code should be clean, well-organized, and compliant with the specified linting and formatting rules.
