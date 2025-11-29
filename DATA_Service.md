# DATA Service

## Overview

The DATA Service is a dedicated background process responsible for ingesting, normalizing, and broadcasting market data to other services (Algo Engine, Web Server). It acts as the central source of truth for real-time and historical data.

## Architecture

The service uses **ZeroMQ** for all external communication, exposing three specific sockets:

1.  **Data Publisher (PUB)**:
    *   **Purpose**: Broadcasts real-time market data (ticks) to subscribers.
    *   **Pattern**: Pub-Sub.
    *   **Binding**: `tcp://{HOST}:{DATA_PUB_PORT}`

2.  **Action Handler (REP)**:
    *   **Purpose**: Handles requests to subscribe/unsubscribe and authorize the broker.
    *   **Pattern**: Request-Reply.
    *   **Binding**: `tcp://{HOST}:{DATA_ACTION_PORT}`

3.  **Snapshot/History Handler (ROUTER)**:
    *   **Purpose**: Handles requests for historical data or current snapshots (LTP, OHLC).
    *   **Pattern**: Router-Dealer (Async).
    *   **Binding**: `tcp://{HOST}:{DATA_ROUTER_PORT}` (Default: 5557)

## Data Formats

### 1. Action Management (REP Socket)

Clients (Algo Engine, Web Server) send JSON requests to manage their data streams and authorization.

#### Authorization Request

*   **Request Format**:

    ```json
    {
        "action": "authorize",
        "broker_id": "zerodha",
        "auth_data": {  // as per broker adapter requirements
            "access_token": "token_string",
            "refresh_token": "token_string"
        },
        "mode": "main" // or "fallback"
    }
    ```

#### Subscription Request

*   **Request Format**:

    ```json
    {
        "action": "subscribe",  // or "unsubscribe"
        "symbol": "INFY"        // or ["INFY", "TCS"]
    }
    ```

*   **Response Format**:

    ```json
    {
        "status": "success",    // or "error"
        "message": "Subscribed to INFY"
    }
    ```

### 2. Real-time Data Publishing (PUB Socket)

Data is published as a **Multipart ZeroMQ Message** consisting of two frames:

*   **Frame 1 (Topic)**: Used for filtering by subscribers.
    *   Format: `market_data.{symbol}` (e.g., `market_data.INFY`)
*   **Frame 2 (Payload)**: JSON encoded market data.
    *   Format:
        ```json
        {
            "symbol": "INFY",
            "timestamp": 1678886400.123,
            "ltp": 1500.50,
            "open": 1490.00,
            "high": 1510.00,
            "low": 1485.00,
            "close": 1500.50,
            "volume": 5000
        }
        ```

### 3. Historical/Snapshot Requests (ROUTER Socket)

*   **Request Format**:
    ```json
    {
        "action": "history",    // or "snapshot"
        "symbol": "INFY",
        "from": "2023-01-01",   // Optional for snapshot
        "to": "2023-01-31",     // Optional for snapshot
        "interval": "1D"        // Optional for snapshot
    }
    ```

## Components

*   **Broker Manager**:
    *   Uses the `app.core.brokers` library.
    *   Manages the actual connection to the broker (e.g., Fyers, Zerodha).
    *   **Modes**: Supports "dummy" (for testing) and "zerodha" (using `app.core.brokers.zerodha`).
    *   **Authentication**: Does **NOT** perform login. It is initialized with an `access_token` provided by the Web Server via the Action Handler.
*   **Subscription Registry**:
    *   Maintains a set of active subscriptions.
    *   Ensures only unique symbols are subscribed to at the broker level.

## Flow

### 1. Startup & Authentication

1.  **Initialization**: Data Service starts and initializes the `Broker Manager` in a "Passive" state.
2.  **Waiting for Auth**: It listens for an `authorize` request on the **Action Handler (REP)** socket from the Web Server.
3.  **Activation**: Upon receiving the token, it initializes the specific Broker Adapter (e.g., `FyersBroker`) and establishes the WebSocket connection.

### 2. Subscription Workflow

1.  **Client Request**: Client sends `{"action": "subscribe", "symbol": "SBIN"}` (or list of symbols) to **REP** socket.
2.  **Registry Update**: Service adds `SBIN` to its internal registry.
3.  **Broker Subscription**: Service calls `broker_manager.subscribe("SBIN")`.
4.  **Ack**: Service replies with `{"status": "success"}`.

### 3. Data Distribution

1.  **Ingestion**: Broker Adapter receives a tick for `SBIN`.
2.  **Normalization**: Tick is converted to the standard JSON format.
3.  **Broadcast**: Service publishes `["market_data.SBIN", JSON_PAYLOAD]` to the **PUB** socket.

## Usage Example

```python
# app/main.py (Lifespan)
from app.data.service import data_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start Data Service as a background task
    task = asyncio.create_task(data_service.start())
    yield
    # Stop Data Service
    data_service.stop()
    await task
```