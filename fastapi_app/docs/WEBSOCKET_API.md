# FastAPI WebSocket API Documentation

This document outlines the structure, authentication, and available actions for the WebSocket API.

## 1. Overview

The WebSocket API provides real-time market data streaming. The architecture consists of a single entry point that delegates connection handling to a centralized `WebSocketProxyService`. This service manages the entire client lifecycle, including authentication, subscriptions, and message broadcasting.

- **Entry Point**: `/api/v1/ws`
- **Core Service**: `fastapi_app.services.websocket_proxy_service.WebSocketProxyService`

## 2. Connection Lifecycle

1.  **Connection**: A client establishes a WebSocket connection to the `/api/v1/ws` endpoint.
2.  **Authentication**: The client **must** send an `authenticate` message as its first action. The server will not process any other messages until authentication is successful.
3.  **Message Exchange**: Once authenticated, the client can send and receive messages for subscribing to market data, unsubscribing, and other actions.
4.  **Disconnection**: When the client disconnects, the server cleans up all associated resources, including subscriptions.

## 3. Authentication

Authentication is performed by sending a JSON message with an `action` of `authenticate` and a valid `api_key`.

**Example Authentication Request:**
```json
{
  "action": "authenticate",
  "api_key": "your_secret_api_key_here"
}
```

**Authentication Responses:**

- **Success:**
  ```json
  {
    "type": "auth_status",
    "status": "success",
    "message": "Authenticated successfully"
  }
  ```
- **Failure:**
  ```json
  {
    "status": "error",
    "code": "AUTHENTICATION_ERROR",
    "message": "Invalid API key"
  }
  ```
  The connection will be closed after a failed authentication attempt.

## 4. Message Format

All messages between the client and server are in JSON format. Each message should contain an `action` (or `type`) field that specifies the requested operation.

## 5. Available Actions

### `subscribe`
Subscribes the client to one or more market data streams.

**Request:**
```json
{
  "action": "subscribe",
  "symbols": [
    { "symbol": "NIFTY", "exchange": "NSE" },
    { "symbol": "SENSEX", "exchange": "BSE" }
  ],
  "mode": "LTP"
}
```
- `symbols`: A list of symbol objects.
- `mode`: The subscription mode. Can be `LTP`, `Quote`, or `Depth`. Defaults to `Quote`.

### `unsubscribe` / `unsubscribe_all`
Unsubscribes the client from specific streams or all current subscriptions.

**Unsubscribe from specific symbols:**
```json
{
  "action": "unsubscribe",
  "symbols": [
    { "symbol": "NIFTY", "exchange": "NSE", "mode": "LTP" }
  ]
}
```

**Unsubscribe from all symbols:**
```json
{
  "action": "unsubscribe_all"
}
```

### `get_broker_info`
Retrieves information about the broker associated with the client's API key.

**Request:**
```json
{
  "action": "get_broker_info"
}
```

### `get_supported_brokers`
Retrieves a list of all brokers supported by the service.

**Request:**
```json
{
  "action": "get_supported_brokers"
}
```

## 6. Error Handling

If an error occurs, the server will send a JSON message with a `status` of `error`.

**Example Error Response:**
```json
{
  "status": "error",
  "code": "INVALID_ACTION",
  "message": "Invalid action: some_action"
}
```
