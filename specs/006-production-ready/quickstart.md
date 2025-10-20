# Quickstart Guide: OpenAlgo FastAPI

This guide provides a comprehensive overview of how to set up, configure, run, and interact with the OpenAlgo FastAPI application.

## 1. Project Overview

OpenAlgo FastAPI is a high-performance trading application backend built with FastAPI, designed for reliability, scalability, and ease of deployment. It provides real-time market data, order management, and account information, integrated with various broker APIs.

## 2. Prerequisites

Before you begin, ensure you have the following installed:

*   **Python 3.10+**: [Download Python](https://www.python.org/downloads/)
*   **Poetry**: For dependency management.
    ```bash
    pip install poetry
    ```
*   **Docker & Docker Compose** (Optional, but recommended for development and production deployments):
    *   [Docker Desktop](https://www.docker.com/products/docker-desktop) (for macOS/Windows)
    *   [Docker Engine & Compose](https://docs.docker.com/engine/install/) (for Linux)
*   **Git**: [Download Git](https://git-scm.com/downloads)

## 3. Installation Steps

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-repo/openalgo-fastapi.git
    cd openalgo-fastapi
    ```
2.  **Install dependencies using Poetry**:
    ```bash
    poetry install
    ```
3.  **Activate the virtual environment**:
    ```bash
    poetry shell
    ```

## 4. Configuration

The application uses environment variables for configuration. Create a `.env` file in the project root based on `.env.example`.

**Essential environment variables**:

*   `APP_KEY`: A strong secret key for session management and CSRF protection.
*   `APP_HOST_IP`: Host IP for the application (e.g., `0.0.0.0`).
*   `APP_PORT`: Port for the application (e.g., `8000`).
*   `LOG_LEVEL`: Logging level (e.g., `INFO`, `DEBUG`, `WARNING`, `ERROR`, `CRITICAL`).
*   `LOG_TO_FILE`: `True` to enable file logging, `False` otherwise.
*   `LOG_DIR`: Directory for log files (if `LOG_TO_FILE` is `True`).
*   `LOG_RETENTION`: Number of days to retain log files.
*   `DATABASE_URL`: SQLAlchemy database connection string (e.g., `sqlite:///./sql_app.db`).

## 5. Running the Application

### A. Development Mode (using Poetry)

1.  Activate the Poetry shell: `poetry shell`
2.  Run the FastAPI application:
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    The `--reload` flag enables hot-reloading for development.

### B. Production Mode (using Docker Compose)

1.  Ensure Docker is running.
2.  Build and run the Docker containers:
    ```bash
    docker-compose up --build -d
    ```
    The `-d` flag runs the containers in detached mode.

## 6. Accessing the API

Once the application is running, you can access:

*   **API Documentation (Swagger UI)**: `http://<APP_HOST_IP>:<APP_PORT>/docs`
*   **Alternative API Docs (Redoc)**: `http://<APP_HOST_IP>:<APP_PORT>/redoc`
*   **Application Root**: `http://<APP_HOST_IP>:<APP_PORT>/`

### Example API Endpoint

You can test the `/test` endpoint:
```bash
curl http://localhost:8000/test
```

## 7. Running Tests

To run the unit tests:

1.  Activate the Poetry shell: `poetry shell`
2.  Run pytest from the project root:
    ```bash
    pytest
    ```

For specific test modules:
```bash
pytest test/unit/app/core/models/test_tradingview_models.py
```
