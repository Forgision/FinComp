# Scalable Python Project Design Principles

This document outlines the core design principles for creating a scalable and maintainable Python application, based on the provided video transcript. These principles guide the project's architecture, folder structure, and development practices.

## 1. Core Scalability Goals

The project should be designed to scale effectively in four key areas:

*   **Size:** The architecture should accommodate a growing codebase without requiring significant refactoring.
*   **Team:** The structure should provide clear boundaries and predictable locations for features, enabling multiple developers to work concurrently.
*   **Environments:** Switching between development, staging, and production environments should be seamless and reliable, with centralized configuration.
*   **Speed:** The development lifecycle should be fast, with quick test execution and an easy-to-set-up local environment.

## 2. Folder Structure

A balanced and intuitive folder structure is crucial. The structure should be organized but not so deeply nested that it becomes difficult to navigate.

```
/
├── app/
│   ├── backend/              # Backend source code (FastAPI)
│   │   ├── api/              # HTTP layer (e.g., FastAPI routers)
│   │   │   └── v1/
│   │   ├── models/           # Pydantic schemas (request/response contracts)
│   │   └── services/         # Business logic layer
│   ├── core/                 # Cross-cutting concerns (config, logging)
│   ├── db/                   # Database schema and session management
│   └── frontend/             # Frontend source code
│       ├── static/           # Static assets (CSS, JS, images)
│       └── templates/        # HTML templates
├── test/                 # Test code, mirroring the 'app/backend' structure
├── .env                  # Local environment variables (not committed)
├── Dockerfile            # Instructions for building the application container
├── docker-compose.yml    # Local development orchestration
└── pyproject.toml        # Project dependencies and tooling configuration
```

## 3. Architectural Principles

*   **Thin API Layer:** The API routes (e.g., FastAPI routers) should be minimal. Their sole responsibility is to handle HTTP requests, delegate to the service layer, and return HTTP responses. No business logic should reside here.
*   **Service Layer for Business Logic:** All business logic must be encapsulated within the `services` folder. This promotes separation of concerns, makes the logic reusable, and allows it to be tested independently of the web framework.
*   **Clear Separation of Concerns:**
    *   **API:** Handles HTTP concerns.
    *   **Services:** Contains business logic.
    *   **Database:** Manages data persistence.
    *   **Core:** Implements cross-cutting concerns.
*   **Dependency Injection:**
    *   Utilize the web framework's built-in dependency injection system (e.g., FastAPI's `Depends`) for wiring components together.
    *   Inject dependencies like database sessions into services, and services into API routes. This facilitates decoupling and simplifies testing by allowing for easy mocking.

## 4. Configuration Management

*   **Centralized Configuration:** All configuration should be managed in a single place, such as `app/core/config.py`.
*   **Use Pydantic Settings:** Leverage `pydantic-settings` to create a robust, type-safe configuration object that can load settings from environment variables, `.env` files, and default values.
*   **Environment-Specific Settings:** Sensitive information and environment-specific values (e.g., database credentials) should be loaded from environment variables.

## 5. Testing Strategy

*   **Test Isolation:** Keep test code in a separate top-level `test` directory. The internal structure of the `test` directory should mirror the `app/backend` directory for easy navigation.
*   **In-Memory Database for Tests:** Use a fast, in-memory database like SQLite for unit and integration tests to ensure they are isolated and run quickly.
*   **Override Dependencies in Tests:** Use the dependency injection system to replace production dependencies (like the database) with test-specific versions (e.g., a test database session).
*   **Mock External Services:** Avoid making real network calls to external services in your tests. Mock these dependencies to keep tests fast and reliable.

## 6. Tooling and Environment

*   **Modern Tooling:** Use modern, efficient tools like `uv` for dependency and environment management.
*   **Containerization:** Use Docker to create consistent and reproducible environments.
    *   A `Dockerfile` defines the production-ready application image.
    *   A `docker-compose.yml` file is used to orchestrate the local development environment, making it closely resemble the production setup.
*   **Consistent Imports:** Configure tools like `pytest` to ensure that module imports in test files are identical to those in the application code, improving clarity and consistency.