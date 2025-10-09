# OpenAlgo System Architecture

## Executive Summary

OpenAlgo is a sophisticated, broker-agnostic algorithmic trading platform built with Python FastAPI that provides a unified API interface for 25+ Indian stock brokers. The platform enables algorithmic trading strategies through REST APIs, WebSocket connections, and an intuitive web interface.

## Design Principles

The architectural decisions in this project are guided by a set of design principles for creating scalable and maintainable Python applications. These principles are documented in detail in the [Scalable Python Project Design Principles](design.md) document.

## Architectural Style

OpenAlgo employs a **Modular Monolithic Architecture** with a **RESTful API** interface, combining the benefits of monolithic simplicity with modular organization through FastAPI Routers and service layers.

### Key Architectural Principles
*   **Broker Abstraction:** Unified interface abstracting broker-specific implementations
*   **Service-Oriented Design:** Clear separation between presentation, business logic, and data layers
*   **Plugin Architecture:** Dynamic broker adapter loading and configuration
*   **Security by Design:** Multi-layered security with encryption, authentication, and authorization
*   **Scalability Ready:** Connection pooling, caching strategies, and horizontal scaling support
*   **Real-time Capabilities:** WebSocket proxy for live market data streaming
*   **Process Isolation:** Strategy execution in isolated processes for stability

## Technology Stack

### Core Technologies
*   **Programming Language:** Python 3.8+ with full type hints support
*   **Web Framework:** FastAPI with modular Router architecture
*   **API Framework:** FastAPI with automatic OpenAPI/Swagger documentation
*   **Database ORM:** SQLAlchemy 2.0+ with connection pooling (50 base, 100 max overflow)
*   **Database Support:** SQLite (development), PostgreSQL/MySQL (production)

### Security & Authentication
*   **Password Hashing:** Argon2 with pepper for enhanced security
*   **API Authentication:** API key-based with Argon2 hashing
*   **Encryption:** Fernet symmetric encryption for sensitive data
*   **2FA Support:** TOTP (Time-based One-Time Password)
*   **Session Management:** Secure cookies with daily expiry at 3:30 AM IST
*   **CSRF Protection:** fastapi-csrf-protect with secure cookie settings

### Real-time & Communication
*   **WebSocket Server:** Standalone proxy with ZeroMQ backend
*   **Real-time Updates:** FastAPI-SocketIO for dashboard updates
*   **Message Queue:** ZeroMQ for broker communication
*   **Telegram Integration:** python-telegram-bot for notifications
*   **Event Loop:** asyncio-based asynchronous processing

### Frontend & UI
*   **Template Engine:** Jinja2 with auto-escaping
*   **CSS Framework:** TailwindCSS with DaisyUI components
*   **JavaScript:** Vanilla ES6+ with Socket.IO client
*   **Theme Support:** Dark/light mode with localStorage persistence
*   **Responsive Design:** Mobile-first responsive layout

### Performance & Monitoring
*   **Rate Limiting:** slowapi with per-key limits
*   **Caching:** Session-based TTL cache
*   **Logging:** Colored logging with sensitive data filtering
*   **Monitoring:** Built-in latency and traffic analysis
*   **Connection Pooling:** httpx with connection reuse

### Deployment & Infrastructure
*   **WSGI Server:** Gunicorn (Linux) / Waitress (Windows)
*   **Process Manager:** Systemd (Linux) / Windows Service
*   **Container Support:** Docker with docker-compose
*   **Cloud Support:** AWS Elastic Beanstalk ready
*   **Environment Management:** python-dotenv with validation

## Directory Structure

```
/
├── app/
│   ├── auth/                 # Old auth router
│   ├── core/                 # Cross-cutting concerns (config, logging)
│   ├── db/                   # Database schema and session management
│   ├── models/               # Old Pydantic schemas
│   ├── services/             # Old business logic layer
│   ├── utils/                # Old utility functions
│   └── web/                  # New structure root
│       ├── main.py           # Main application entrypoint
│       ├── backend/          # New backend source code (FastAPI)
│       │   └── api/
│       │       └── v1/       # API version 1 routers
│       └── frontend/         # New frontend source code
│           ├── static/       # Static assets (CSS, JS, images)
│           └── templates/    # HTML templates
├── test/                     # Test code
├── .env                      # Local environment variables (not committed)
├── Dockerfile                # Instructions for building the application container
├── docker-compose.yml        # Local development orchestration
└── pyproject.toml            # Project dependencies and tooling configuration
```

## Component Diagram (Mermaid)

```mermaid
graph TD
    subgraph "Client Layer"
        WebUI[Web Browser UI]
        APIClient[External API Client]
        WSClient[WebSocket Client]
    end

    subgraph "OpenAlgo Application - FastAPI"
        direction TB
        APILayer[API Layer - FastAPI - Routers]
        Auth[Auth & Session Mgmt]
        RateLimiter[Rate Limiter]
        SocketIO[WebSocket - FastAPI-SocketIO]
        CoreLogic[Core Application Logic]
        StrategyEngine[Strategy Engine - strategies]
        BrokerInterface[Broker Interface - broker]
        DBLayer[Database Layer - SQLAlchemy]
        Utils[Utilities - utils]
        LoggingSystem[Centralized Logging System]
    end

    subgraph "WebSocket Infrastructure"
        direction TB
        WSProxy[WebSocket Proxy Server]
        BrokerAdapters[Broker WebSocket Adapters]
        ZMQBroker[ZeroMQ Message Broker]
        AdapterFactory[Broker Adapter Factory]
    end

    subgraph "External Systems"
        DB[(Database)]
        BrokerAPI1[Broker A API]
        BrokerAPI2[Broker B API]
        BrokerAPIn[... Broker N API]
        BrokerWS1[Broker A WebSocket]
        BrokerWS2[Broker B WebSocket]
        BrokerWSn[... Broker N WebSocket]
    end

    %% Main Application Flow
    WebUI --> APILayer
    APIClient --> APILayer
    APILayer --> Auth
    APILayer --> RateLimiter
    APILayer --> CoreLogic
    APILayer --> SocketIO
    CoreLogic --> StrategyEngine
    CoreLogic --> BrokerInterface
    CoreLogic --> DBLayer
    Auth --> DBLayer
    StrategyEngine --> BrokerInterface
    BrokerInterface --> BrokerAPI1
    BrokerInterface --> BrokerAPI2
    BrokerInterface --> BrokerAPIn
    DBLayer --> DB
    
    %% WebSocket Flow
    WSClient --> WSProxy
    WSProxy --> AdapterFactory
    AdapterFactory --> BrokerAdapters
    BrokerAdapters --> ZMQBroker
    ZMQBroker --> WSProxy
    WSProxy --> WSClient
    BrokerAdapters --> BrokerWS1
    BrokerAdapters --> BrokerWS2
    BrokerAdapters --> BrokerWSn
    
    %% Utility Dependencies
    APILayer --> Utils
    CoreLogic --> Utils
    BrokerInterface --> Utils
    DBLayer --> Utils
    Auth --> Utils
    WSProxy --> Utils
    BrokerAdapters --> Utils
    
    %% Logging System
    APILayer --> LoggingSystem
    CoreLogic --> LoggingSystem
    BrokerInterface --> LoggingSystem
    WSProxy --> LoggingSystem
    BrokerAdapters --> LoggingSystem
    Utils --> LoggingSystem