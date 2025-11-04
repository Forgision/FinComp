# WebSocket Proxy Refactoring Tasks

## Completed

- Identified the root cause of test failures: an architectural mismatch between the standalone `websockets` server and FastAPI's `starlette.websockets`.
- Removed the standalone server logic (`start`, `stop` methods, and related attributes) from `WebSocketProxyService`.
- Renamed `handle_client` to `handle_fastapi_websocket` and updated the WebSocket parameter to use `starlette.websockets.WebSocket`.

## To Do

- Refactor the `handle_fastapi_websocket` method to replace all `websockets` library calls with `starlette.websockets` equivalents for receiving, sending, and closing connections.
- Update the exception handling to catch `starlette.websockets.WebSocketDisconnect`.
- Update all other methods that interact with the WebSocket object (`authenticate_client`, `send_message`, `send_error`, `cleanup_client`) to use the `starlette.websockets.WebSocket` API.
- Modify the FastAPI WebSocket endpoint in `fastapi_app/api/v1/endpoints/websocket.py` to call the new `handle_fastapi_websocket` method.
- Rerun the tests and verify that the WebSocket test failures are resolved.
- Once WebSocket tests are passing, re-address the `jinja2.exceptions.TemplateNotFound` error.
