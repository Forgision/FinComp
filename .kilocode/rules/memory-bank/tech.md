# Technology Stack

This document outlines the technologies, development setup, and technical constraints for the OpenAlgo algorithmic trading platform.

## Core Technologies
*   **Programming Language:** Python 3.8+ with full type hints support
*   **Web Framework:** FastAPI with a modular Router architecture for organizing routes and views.
*   **API Framework:** FastAPI for building RESTful APIs, providing automatic OpenAPI/Swagger documentation, request parsing, and response marshalling.
*   **Database ORM:** SQLAlchemy 2.0+ is used for object-relational mapping, enabling database-agnostic operations.
*   **Database Support:**
    *   SQLite for development and testing.
    *   PostgreSQL or MySQL for production environments.
*   **Database Migrations:** Alembic for managing and versioning the database schema.

## Security & Authentication
*   **Password Hashing:** Argon2 (specifically Argon2id) with a pepper for securely hashing user passwords and API keys.
*   **Encryption:** Fernet (from the `cryptography` library) for symmetric encryption of sensitive data at rest, such as broker credentials, API keys, and TOTP secrets.
*   **Two-Factor Authentication (2FA):** Time-based One-Time Password (TOTP) support using `pyotp`.
*   **Session Management:** JWT-based secure, signed cookies for managing web UI sessions, with a daily expiry mechanism.
*   **CSRF Protection:** `fastapi-csrf-protect` is used to protect against Cross-Site Request Forgery attacks on web forms.

## Real-time & Communication
*   **WebSocket Server:** A standalone, asynchronous WebSocket proxy server for real-time market data streaming.
*   **Internal Messaging:** ZeroMQ (ZMQ) is used as a high-performance message queue for communication between the WebSocket proxy and broker adapters.
*   **Dashboard Updates:** FastAPI-SocketIO for real-time updates on the web dashboard.
*   **Telegram Integration:** `python-telegram-bot` library for integrating with the Telegram Bot API.
*   **Asynchronous Operations:** `asyncio` is used for handling asynchronous tasks, particularly within the Telegram bot service.

## Frontend & UI
*   **Template Engine:** Jinja2 for rendering dynamic HTML templates.
*   **CSS Framework:** TailwindCSS, complemented by the DaisyUI component library for styling the web interface.
*   **JavaScript:** Vanilla ES6+ for client-side interactivity, including the Socket.IO client for real-time communication.
*   **Charting:** Plotly is used for generating market data charts, which are rendered into images using the Kaleido engine for display in the Telegram bot.

## Performance & Monitoring
*   **Rate Limiting:** `slowapi` for implementing rate limits on API endpoints and sensitive operations like login attempts.
*   **HTTP Client:** `httpx` is used as the modern, async-capable HTTP client for making requests to external broker APIs, featuring connection pooling.
*   **Caching:** A session-based Time-To-Live (TTL) cache is implemented for temporary data storage.
*   **Logging:** A custom, centralized logging system with colored output (`colorama`), automatic log rotation, and a `SensitiveDataFilter` to redact confidential information.

## Strategy Hosting & Scheduling
*   **Scheduling:** `APScheduler` (Advanced Python Scheduler) is used for cron-like scheduling of Python trading strategies.
*   **Process Management:** The `subprocess` module is used to run trading strategies in isolated processes, with platform-specific configurations for Windows and Linux/macOS.

## Deployment & Infrastructure
*   **WSGI Server:**
    *   Gunicorn for production deployments on Linux.
    *   Waitress for production deployments on Windows.
*   **Process Manager:**
    *   Systemd for managing the application as a service on Linux.
    *   Windows Service integration for Windows deployments.
*   **Reverse Proxy:** Nginx is recommended for production deployments on Linux to handle SSL termination, serve static files, and act as a reverse proxy.
*   **Containerization:** Docker and `docker-compose` are supported for creating consistent development and deployment environments.
*   **Cloud Support:** The application is designed to be compatible with AWS Elastic Beanstalk.
*   **Environment Management:** `python-dotenv` is used to load configuration from `.env` files.

## Dependencies
*   **Python:** Backend dependencies are managed with `pip` and are listed in the `requirements.txt` file. `uv` is used in deployment scripts for faster installation.
*   **JavaScript:** Frontend dependencies are managed with `npm` and are listed in the `package.json` file.

## Python Environment Management
*   **Package Installation:** All Python packages must be installed using the `uv add` command. Native `pip` commands must not be used. This ensures consistency and leverages `uv`'s performance benefits.
*   **Application Execution:** All Python scripts and applications should be run using the `uv run` command.